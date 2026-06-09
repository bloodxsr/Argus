package main

import (
	"encoding/json"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/nats-io/nats.go"
	"crypto/subtle"
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

	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://nats:4222"
	}
	nc, err := nats.Connect(natsURL)
	if err != nil {
		log.Printf("Warning: Failed to connect to NATS: %v", err)
	} else {
		log.Println("Connected to NATS")
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

	// Authentication middleware
	authMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			expectedToken := os.Getenv("AGRUS_SENSOR_TOKEN")
			if expectedToken == "" {
				expectedToken = "default-secure-token" // Fallback, should be set in prod
			}

			authHeader := r.Header.Get("Authorization")
			const prefix = "Bearer "
			if len(authHeader) < len(prefix) || authHeader[:len(prefix)] != prefix {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			token := authHeader[len(prefix):]
			if subtle.ConstantTimeCompare([]byte(token), []byte(expectedToken)) != 1 {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			next.ServeHTTP(w, r)
		})
	}

	// Sensor Telemetry Ingestion (High Throughput via Goroutines)
	r.With(authMiddleware).Post("/api/v1/telemetry", func(w http.ResponseWriter, r *http.Request) {
		var event TelemetryEvent
		if err := json.NewDecoder(r.Body).Decode(&event); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		log.Printf("Received Kernel Event: [%s] from host %s", event.EventType, event.Host)
		
		// Fanout to AI Engine in background
		go routeToAIEngine(event, nc)

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

func routeToAIEngine(event TelemetryEvent, nc *nats.Conn) {
	if nc == nil {
		log.Println("NATS not connected, dropping event")
		return
	}
	jsonData, _ := json.Marshal(event)
	err := nc.Publish("incidents.scored", jsonData)
	if err != nil {
		log.Printf("Failed to publish to NATS: %v", err)
	} else {
		log.Printf("Successfully routed event %s to NATS", event.EventID)
	}
}
