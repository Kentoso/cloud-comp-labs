package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"math/rand"
	"time"

	"github.com/lionell/parcs/go/parcs"
)

type MonteCarlo struct {
	*parcs.Service
}

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

func (m *MonteCarlo) sampleFunction(generator *rand.Rand, a float64, b float64) *big.Float {
	x := a + (b-a)*generator.Float64()
	square := new(big.Float).Mul(big.NewFloat(x), big.NewFloat(x))
	one := big.NewFloat(1)

	oneMinusSquare := new(big.Float).Sub(one, square)

	result := new(big.Float).Sqrt(oneMinusSquare)

	return result
}

func (m *MonteCarlo) Run() {
	var n int

	log.Print("Receiving n")

	if err := m.Recv(&n); err != nil {
		panic("Error while receiving n")
	}

	log.Print("Receiving a")

	var a float64
	if err := m.Recv(&a); err != nil {
		panic("Error while receiving a")
	}

	log.Print("Receiving b")

	var b float64
	if err := m.Recv(&b); err != nil {
		panic("Error while receiving b")
	}

	log.Printf("Received n=%d, a=%f, b=%f. Calculating...", n, a, b)

	generator := rand.New(rand.NewSource(time.Now().UnixNano()))

	startTime := time.Now()

	total := big.NewFloat(0)
	for i := 0; i < n; i++ {
		total.Add(total, m.sampleFunction(generator, a, b))
	}

	execTime := time.Since(startTime).Seconds()

	log.Printf("Sending result...")

	err := m.Send(Result{
		Sum: *total, Time: execTime,
	})
	if err != nil {
		panic("Error during sending result")
	}

}

func main() {
	parcs.Exec(&MonteCarlo{parcs.DefaultService()})
}
