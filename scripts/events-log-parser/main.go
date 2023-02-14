package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"log"
	"os"
	"time"
)

const (
	dateTimeLayout    = "2006-01-02T15:04:05.9999999Z"
	eventUserLoggedIn = "User_LoggedIn"
)

func main() {
	p := flag.String("log", "logs/bitwarden-events_export.csv", "Bitwarden event log csv file")
	flag.Parse()

	records, err := readCSV(*p)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("\nLast 3 days daily logins average: %f\n", averageDailyLogins(records, 3))
	fmt.Printf("\nLast 5 days daily logins average: %f\n\n", averageDailyLogins(records, 5))

	// printDailyLogins(records)

	fmt.Printf("\nLast 3 days daily unique user logins average: %f\n", averageDailyUniqueUserLogins(records, 3))
	fmt.Printf("\nLast 5 days daily unique user logins average: %f\n\n", averageDailyUniqueUserLogins(records, 5))

	// printDailyUniqueUserLogins(records)
}

type record struct {
	message, appIcon, appName, userID, userName, userEmail, ip, eventType, installationID string
	timestamp                                                                             time.Time
}

type loginsCount struct {
	day   time.Time
	count int
}

func readCSV(p string) ([]record, error) {

	f, err := os.Open(p)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	lines, err := csv.NewReader(f).ReadAll()
	if err != nil {
		return nil, err
	}

	records := []record{}

	for _, l := range lines[1:] {
		ts, err := time.Parse(dateTimeLayout, l[6])
		if err != nil {
			return nil, err
		}

		r := record{
			message:        l[0],
			appIcon:        l[1],
			appName:        l[2],
			userID:         l[3],
			userName:       l[4],
			userEmail:      l[5],
			timestamp:      ts,
			ip:             l[7],
			eventType:      l[8],
			installationID: l[9],
		}
		records = append(records, r)
	}

	return records, err
}

func dailyLoginsCount(records []record) map[string]int {
	m := make(map[string]int)
	for _, r := range records {
		if r.eventType == eventUserLoggedIn {
			d := r.timestamp.Format("2006-01-02")
			if _, ok := m[d]; !ok {
				m[d] = 1
			} else {
				m[d] = m[d] + 1
			}

		}
	}

	return m
}

func averageDailyLogins(records []record, num int) float64 {
	m := make(map[string]int)
	days := []string{}

	for _, r := range records {
		if r.eventType == eventUserLoggedIn {
			d := r.timestamp.Format("2006-01-02")
			if _, ok := m[d]; !ok {
				m[d] = 1
				days = append(days, d)
			} else {
				m[d] = m[d] + 1
			}
		}
	}

	e := len(m)
	if num < len(m) {
		e = num
	}

	sum := 0
	for _, d := range days[:e] {
		sum = sum + m[d]
	}

	return float64(sum) / float64(len(days[:e]))
}

func printDailyLogins(records []record) {
	dailyLogins := dailyLoginsCount(records)

	fmt.Println("Daily Logins:")
	for k, v := range dailyLogins {
		fmt.Printf("%s | %d\n", k, v)
	}
}

func dailyUniqueUserLoginsCount(records []record) map[string]int {
	m := make(map[string]int)
	u := make(map[string]bool)
	for _, r := range records {
		if r.eventType == eventUserLoggedIn {
			d := r.timestamp.Format("2006-01-02")
			if _, ok := m[d]; !ok {
				m[d] = 1
				u[r.userName] = true
			} else {
				if _, ok := u[r.userName]; !ok {
					m[d] = m[d] + 1
					u[r.userName] = true
				}
			}
		}
	}

	return m
}

func averageDailyUniqueUserLogins(records []record, num int) float64 {
	m := make(map[string]int)
	days := []string{}
	u := make(map[string]bool)
	for _, r := range records {
		if r.eventType == eventUserLoggedIn {
			d := r.timestamp.Format("2006-01-02")
			if _, ok := m[d]; !ok {
				m[d] = 1
				u[r.userName] = true
				days = append(days, d)
			} else {
				if _, ok := u[r.userName]; !ok {
					m[d] = m[d] + 1
					u[r.userName] = true
				}
			}
		}
	}

	e := len(m)
	if num < len(m) {
		e = num
	}

	sum := 0
	for _, d := range days[:e] {
		sum = sum + m[d]
	}

	return float64(sum) / float64(len(days[:e]))
}

func printDailyUniqueUserLogins(records []record) {
	dailyUniqueUserLogins := dailyUniqueUserLoginsCount(records)

	fmt.Println("Daily Unique User Logins:")
	for k, v := range dailyUniqueUserLogins {
		fmt.Printf("%s | %d\n", k, v)
	}
}
