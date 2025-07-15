package function

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"math/rand"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type FunInput struct {
	Size  string
	Debug string
}

type RetValType struct {
	Result      map[string]string  `json:"result"`
	Measurement map[string]float64 `json:"measurement"`
}

var sizeGenerators = map[string]int{
	"test":    10,
	"tiny":    100,
	"small":   1000,
	"medium":  10000,
	"large":   100000,
	"huge":    1000000,
	"massive": 10000000,
}

const htmlTemplate = `
<!DOCTYPE html>
<html>
  <head>
    <title>Randomly generated data.</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css" rel="stylesheet" media="screen">
    <style type="text/css">
      .container {
        max-width: 500px;
        padding-top: 100px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <p>Welcome {{.Username}}!</p>
      <p>Data generated at: {{.CurTime}}!</p>
      <p>Requested random numbers:</p>
      <ul>
        {{range .RandomNumbers}}
          <li>{{.}}</li>
        {{end}}
      </ul>
    </div>
  </body>
</html>
`

func inputSize(size string) int {
	if s, ok := sizeGenerators[size]; ok {
		return s
	}
	if i, err := strconv.Atoi(size); err == nil {
		return i
	}
	return 1
}

func dynamicHtml(input *FunInput) *RetValType {
	retVal := &RetValType{
		Result:      make(map[string]string),
		Measurement: make(map[string]float64),
	}

	key := "1"
	debug := false
	if input != nil {
		if input.Size != "" {
			key = input.Size
		}
		if strings.ToLower(input.Debug) == "true" {
			debug = true
		}
	}

	loadSize := inputSize(key)
	if debug {
		log.Printf("Starting DynamicHtml: %s\n", key)
	}

	startTime := time.Now()

	initStart := time.Now()
	tmpl, err := template.New("webpage").Parse(htmlTemplate)
	if err != nil {
		log.Fatalf("Template parsing failed: %v", err)
	}
	initEnd := time.Now()

	setupStart := time.Now()
	rand.Seed(time.Now().UnixNano())
	numbers := make([]int, loadSize)
	for i := 0; i < loadSize; i++ {
		numbers[i] = rand.Intn(1000000)
	}
	setupEnd := time.Now()

	data := map[string]interface{}{
		"Username":      "testname",
		"CurTime":       time.Now().Format("2006-01-02 15:04:05"),
		"RandomNumbers": numbers,
	}

	renderStart := time.Now()
	var rendered bytes.Buffer
	err = tmpl.Execute(&rendered, data)
	if err != nil {
		log.Fatalf("Template execution failed: %v", err)
	}
	renderEnd := time.Now()

	retVal.Result["input_size"] = key
	retVal.Result["converted_size"] = strconv.Itoa(loadSize)
	retVal.Result["rendered_Length"] = strconv.Itoa(rendered.Len())

	retVal.Measurement["total_run_time"] = renderEnd.Sub(startTime).Seconds()
	retVal.Measurement["init_time"] = initEnd.Sub(initStart).Seconds()
	retVal.Measurement["setup_time"] = setupEnd.Sub(setupStart).Seconds()
	retVal.Measurement["render_time"] = renderEnd.Sub(renderStart).Seconds()
	retVal.Measurement["input_size"] = float64(loadSize)
	retVal.Measurement["render_size"] = float64(rendered.Len())

	if debug {
		retVal.Result["rendered_HTML"] = rendered.String()
	}

	log.Printf("retVal.measurement=%v\n", retVal.Measurement)
	return retVal
}

func Handle(w http.ResponseWriter, r *http.Request) {
	var input FunInput
	if r.Method == http.MethodPost {
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			http.Error(w, "Invalid JSON input", http.StatusBadRequest)
			return
		}
	} else {
		input = FunInput{
			Size:  r.URL.Query().Get("size"),
			Debug: r.URL.Query().Get("debug"),
		}
	}
	ret := dynamicHtml(&input)

	if html, ok := ret.Result["rendered_HTML"]; ok {
		w.Header().Set("Content-Type", "text/html")
		fmt.Fprint(w, html)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ret)
}

