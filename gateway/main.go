package main

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/nats-io/nats.go"
)

 
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
	expectedToken := os.Getenv("AGRUS_SENSOR_TOKEN")
	if expectedToken == "" {
		log.Fatal("AGRUS_SENSOR_TOKEN is required")
	}

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

	 
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	 
	r.Use(func(next http.Handler) http.Handler {
		allowedOriginsEnv := os.Getenv("AGRUS_ALLOWED_ORIGINS")
		if allowedOriginsEnv == "" {
			allowedOriginsEnv = "http://localhost:4200"
		}
		allowedOrigins := strings.Split(allowedOriginsEnv, ",")

		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			origin := req.Header.Get("Origin")
			allowed := false
			if origin == "" {
				allowed = true
			} else {
				for _, o := range allowedOrigins {
					if strings.TrimSpace(o) == origin {
						allowed = true
						break
					}
				}
			}

			if allowed && origin != "" {
				w.Header().Set("Access-Control-Allow-Origin", origin)
			} else if !allowed && origin != "" {
				http.Error(w, "CORS origin not allowed", http.StatusForbidden)
				return
			}
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
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

	 
	authMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			authHeader := r.Header.Get("Authorization")
			const prefix = "Bearer "
			if len(authHeader) < len(prefix) || authHeader[:len(prefix)] != prefix {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			token := authHeader[len(prefix):]
			
			 
			expectedHash := sha256.Sum256([]byte(expectedToken))
			providedHash := sha256.Sum256([]byte(token))

			if subtle.ConstantTimeCompare(providedHash[:], expectedHash[:]) != 1 {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			next.ServeHTTP(w, r)
		})
	}

	 
	r.With(authMiddleware).Post("/api/v1/telemetry", func(w http.ResponseWriter, r *http.Request) {
		var events []TelemetryEvent
		
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read body", http.StatusBadRequest)
			return
		}

		if len(body) > 0 && body[0] == '[' {
			if err := json.Unmarshal(body, &events); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
		} else {
			var single TelemetryEvent
			if err := json.Unmarshal(body, &single); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			events = append(events, single)
		}

		for _, event := range events {
			log.Printf("Received Kernel Event: [%s] from host %s", event.EventType, event.Host)
			 
			go routeToAIEngine(event, nc)
		}

		w.WriteHeader(http.StatusAccepted)
		w.Write([]byte(`{"status": "queued"}`))
	})

	 
	proxy := httputil.NewSingleHostReverseProxy(target)

	 
	r.With(authMiddleware).Get("/api/scenarios", func(w http.ResponseWriter, req *http.Request) {
		req.URL.Path = "/scenarios"
		proxy.ServeHTTP(w, req)
	})

	 
	r.With(authMiddleware).Post("/api/scenarios/{id}/run", func(w http.ResponseWriter, req *http.Request) {
		id := chi.URLParam(req, "id")
		req.URL.Path = "/scenarios/" + id + "/run"
		proxy.ServeHTTP(w, req)
	})

	proxyPaths := []string{
		"/analyze",
		"/baselines",
		"/baselines/{entity_id}",
		"/baselines/deviation",
		"/correlations",
		"/timeline/{entity}",
		"/containers",
		"/containers/quarantine",
		"/containers/kill",
		"/scan",
		"/remediate",
	}

	for _, p := range proxyPaths {
		r.With(authMiddleware).HandleFunc("/api"+p, func(w http.ResponseWriter, req *http.Request) {
			req.URL.Path = strings.TrimPrefix(req.URL.Path, "/api")
			proxy.ServeHTTP(w, req)
		})
	}

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
