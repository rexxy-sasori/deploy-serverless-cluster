package function

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"time"
)

type RequestPayload struct {
	Size int  `json:"size"`
	Seed *int `json:"seed,omitempty"`
}

type ResponsePayload struct {
	Result struct {
		Order   []int `json:"order"`
		Dist    []int `json:"dist"`
		Parents []int `json:"parents"`
	} `json:"result"`
	Measurement struct {
		GraphGeneratingTime float64 `json:"graph_generating_time"`
		ComputeTime         float64 `json:"compute_time"`
	} `json:"measurement"`
}

type Graph struct {
	Adjacency [][]int
}

func (g *Graph) AddEdge(u, v int) {
	g.Adjacency[u] = append(g.Adjacency[u], v)
	g.Adjacency[v] = append(g.Adjacency[v], u)
}

func (g *Graph) BFS(start int) (order []int, dist []int, parents []int) {
	n := len(g.Adjacency)
	visited := make([]bool, n)
	dist = make([]int, n)
	parents = make([]int, n)
	for i := range parents {
		parents[i] = -1
	}

	queue := []int{start}
	visited[start] = true
	order = append(order, start)

	for len(queue) > 0 {
		u := queue[0]
		queue = queue[1:]

		for _, v := range g.Adjacency[u] {
			if !visited[v] {
				visited[v] = true
				dist[v] = dist[u] + 1
				parents[v] = u
				order = append(order, v)
				queue = append(queue, v)
			}
		}
	}

	return order, dist, parents
}

// Generate a simple Barabási–Albert graph with size nodes and m=10 edges per new node
func GenerateBarabasiAlbertGraph(n int, m int) *Graph {
	graph := &Graph{Adjacency: make([][]int, n)}
	degreeList := []int{}

	// Start with a fully connected core of m nodes
	for i := 0; i < m; i++ {
		for j := i + 1; j < m; j++ {
			graph.AddEdge(i, j)
			degreeList = append(degreeList, i, j)
		}
	}

	// Add new nodes one by one
	for newNode := m; newNode < n; newNode++ {
		targets := map[int]bool{}
		for len(targets) < m {
			idx := rand.Intn(len(degreeList))
			selected := degreeList[idx]
			if selected != newNode {
				targets[selected] = true
			}
		}

		for target := range targets {
			graph.AddEdge(newNode, target)
			degreeList = append(degreeList, newNode, target)
		}
	}

	return graph
}

// Handle an HTTP Request.
func Handle(w http.ResponseWriter, r *http.Request) {
	var req RequestPayload

	if r.Method != http.MethodPost {
		http.Error(w, "Only POST method is supported", http.StatusMethodNotAllowed)
		return
	}

	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil || req.Size <= 0 {
		http.Error(w, "Invalid JSON or missing 'size' field", http.StatusBadRequest)
		return
	}

	if req.Seed != nil {
		rand.Seed(int64(*req.Seed))
	} else {
		rand.Seed(time.Now().UnixNano())
	}

	startGen := time.Now()
	graph := GenerateBarabasiAlbertGraph(req.Size, 10)
	endGen := time.Now()

	startBFS := time.Now()
	order, dist, parents := graph.BFS(0)
	endBFS := time.Now()

	var resp ResponsePayload
	resp.Result.Order = order
	resp.Result.Dist = dist
	resp.Result.Parents = parents
	resp.Measurement.GraphGeneratingTime = float64(endGen.Sub(startGen).Microseconds())
	resp.Measurement.ComputeTime = float64(endBFS.Sub(startBFS).Microseconds())

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
