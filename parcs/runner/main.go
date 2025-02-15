package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"os"
	"strconv"
	"time"

	"github.com/lionell/parcs/go/parcs"
)

type Result struct {
	Sum  big.Float
	Time float64
}

func (r Result) MarshalJSON() ([]byte, error) {
	return json.Marshal(struct {
		Sum  string  `json:"sum"`
		Time float64 `json:"time"`
	}{
		Sum:  r.Sum.Text('f', -1),
		Time: r.Time,
	})
}

func (r *Result) UnmarshalJSON(data []byte) error {
	aux := struct {
		Sum  string  `json:"sum"`
		Time float64 `json:"time"`
	}{}

	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}

	if _, ok := r.Sum.SetString(aux.Sum); !ok {
		return fmt.Errorf("invalid big.Float value: %s", aux.Sum)
	}

	r.Time = aux.Time
	return nil
}

const workerImage = "dsamusknu/parcs-lab-worker-go:latest"

type MonteCarlo struct {
	*parcs.Runner
}

func (m *MonteCarlo) EstimateIntegral(n int, a float64, b float64, workerResults []*big.Float) *big.Float {
	total := big.NewFloat(0)
	for i := 0; i < len(workerResults); i++ {
		total.Add(total, workerResults[i])
	}

	avg := new(big.Float).Quo(total, big.NewFloat(float64(n)))

	result := new(big.Float).Mul(avg, big.NewFloat(float64(b-a)))

	return result
}

type Inputs struct {
	N       int
	A       float64
	B       float64
	Workers int
}

func getInputsFromEnv() Inputs {
	nStr := os.Getenv("N")
	n, err := strconv.Atoi(nStr)
	if err != nil {
		panic(err)
	}

	aStr := os.Getenv("A")
	if aStr == "" {
		aStr = "0"
	}
	a, err := strconv.ParseFloat(aStr, 64)
	if err != nil {
		panic(err)
	}

	bStr := os.Getenv("B")
	if bStr == "" {
		bStr = "1"
	}
	b, err := strconv.ParseFloat(bStr, 64)
	if err != nil {
		panic(err)
	}

	workersStr := os.Getenv("WORKERS")
	workers, err := strconv.Atoi(workersStr)
	if err != nil {
		panic(err)
	}

	return Inputs{
		N:       n,
		A:       a,
		B:       b,
		Workers: workers,
	}
}

func (m *MonteCarlo) Run() {
	inputs := getInputsFromEnv()
	startTime := time.Now()

	log.Printf("Received n=%d, a=%f, b=%f, workers=%d", inputs.N, inputs.A, inputs.B, inputs.Workers)

	log.Print("n=", inputs.N, " workers=", inputs.Workers)

	samplesPerWorker := inputs.N / inputs.Workers

	log.Print("samplesPerWorker=", samplesPerWorker)

	tasks := make([]*parcs.Task, inputs.Workers)

	log.Print("Sending tasks to workers")

	var err error

	for i := 0; i < inputs.Workers; i++ {
		tasks[i], err = m.Engine.Start(workerImage)
		if err != nil {
			panic(err)
		}

		tasks[i].SendAll(samplesPerWorker, inputs.A, inputs.B)
	}

	workersResults := make([]*big.Float, inputs.Workers)

	for i := 0; i < inputs.Workers; i++ {
		var workerResult Result
		err := tasks[i].Recv(&workerResult)
		if err != nil {
			panic(err)
		}
		log.Printf("Worker %d result: %v time taken: %fs", i, workerResult.Sum.Text('f', -1), workerResult.Time)
		workersResults[i] = &workerResult.Sum
	}

	log.Print("Calculating final result")

	piDivFour := m.EstimateIntegral(inputs.N, inputs.A, inputs.B, workersResults)

	pi := new(big.Float).Mul(piDivFour, big.NewFloat(4))

	log.Printf("Pi estimation: %v", pi.Text('f', -1))

	execTime := time.Since(startTime).Seconds()
	log.Printf("Total execution time: %fs", execTime)
}

func main() {
	parcs.Exec(&MonteCarlo{parcs.DefaultRunner()})
}
