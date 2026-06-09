package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// TelemetryEvent matches the schema sent by the Rust eBPF sensor
type TelemetryEvent struct {
	SchemaVersion string `json:"schema_version"`
	EventID       string `json:"event_id"`
	Source        string `json:"source"`
	EventType     string `json:"event_type"`
	Timestamp     string `json:"timestamp"`
	Host          string `json:"host"`
	HostIP        string `json:"host_ip"`
	Environment   string `json:"environment"`
	PID           int    `json:"pid"`
	UID           int    `json:"uid"`
	Payload       map[string]interface{} `json:"payload"`
}

func main() {
	aiURL := os.Getenv("SECURITY_AI_BASE_URL")
	if aiURL == "" {
		aiURL = "http://security-ai:8000"
	}

	target, err := url.Parse(aiURL)
	if err != nil {
		log.Fatalf("Invalid AI URL: %v", err)
	}

	r := chi.NewRouter()

	// High performance enterprise middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	// CORS for MERN stack integration
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			if req.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}
			next.ServeHTTP(w, req)
		})
	})

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("AGRUS Go Gateway Online"))
	})

	// Sensor Telemetry Ingestion (High Throughput via Goroutines)
	r.Post("/api/v1/telemetry", func(w http.ResponseWriter, r *http.Request) {
		var event TelemetryEvent
		if err := json.NewDecoder(r.Body).Decode(&event); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		log.Printf("Received Kernel Event: [%s] from host %s", event.EventType, event.Host)
		
		// Fanout to AI Engine in background
		go routeToAIEngine(event, aiURL)

		w.WriteHeader(http.StatusAccepted)
		w.Write([]byte(`{"status": "queued"}`))
	})

	// Reverse Proxy for the MERN Stack -> Python AI Engine
	proxy := httputil.NewSingleHostReverseProxy(target)

	// Proxy /api/scenarios directly to Python
	r.Get("/api/scenarios", func(w http.ResponseWriter, req *http.Request) {
		req.URL.Path = "/scenarios"
		proxy.ServeHTTP(w, req)
	})

	// Proxy /api/scenarios/{id}/run directly to Python
	r.Post("/api/scenarios/{id}/run", func(w http.ResponseWriter, req *http.Request) {
		id := chi.URLParam(req, "id")
		req.URL.Path = "/scenarios/" + id + "/run"
		proxy.ServeHTTP(w, req)
	})

	log.Println("Starting AGRUS Go Gateway on :8080")
	log.Printf("Proxying AI requests to: %s", aiURL)
	if err := http.ListenAndServe(":8080", r); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}

func routeToAIEngine(event TelemetryEvent, aiURL string) {
	jsonData, _ := json.Marshal(event)
	// For now, map the telemetry to our prototype python endpoint
	resp, err := http.Post(aiURL+"/scenarios/rce_c2_beacon/run", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Failed to reach Python AI Engine: %v", err)
		return
	}
	defer resp.Body.Close()
	log.Printf("Successfully routed event %s to AI Engine", event.EventID)
}
