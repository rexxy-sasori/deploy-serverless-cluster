package function

import (
	"encoding/json"
	"math/rand"
	"net/http"
	"time"

	"github.com/h8gi/go-igraph"
)

type RequestPayload struct {
	Size int  `json:"size"`
	Seed *int `json:"seed,omitempty"`
}

type ResultPayload struct {
	Order   []int `json:"order"`
	Dist    []int `json:"dist"`
	Parents []int `json:"parents"`
}

type MeasurementPayload struct {
	GraphGeneratingTime float64 `json:"graph_generating_time"`
	ComputeTime         float64 `json:"compute_time"`
}

type ResponsePayload struct {
	Result      ResultPayload      `json:"result"`
	Measurement MeasurementPayload `json:"measurement"`
}

func Handle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST method is supported", http.StatusMethodNotAllowed)
		return
	}

	var req RequestPayload
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Size <= 0 {
		http.Error(w, "Invalid JSON or missing 'size' field", http.StatusBadRequest)
		return
	}

	if req.Seed != nil {
		rand.Seed(int64(*req.Seed))
	} else {
		rand.Seed(time.Now().UnixNano())
	}

	genStart := time.Now()
	g := igraph.GenerateBA(req.Size, 10)
	genEnd := time.Now()

	bfsStart := time.Now()
	bfsRes := g.BFS(0)
	bfsEnd := time.Now()

	resp := ResponsePayload{
		Result: ResultPayload{
			Order:   bfsRes.Order,
			Dist:    bfsRes.Dist,
			Parents: bfsRes.Parents,
		},
		Measurement: MeasurementPayload{
			GraphGeneratingTime: float64(genEnd.Sub(genStart).Microseconds()),
			ComputeTime:         float64(bfsEnd.Sub(bfsStart).Microseconds()),
		},
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
	}
}
