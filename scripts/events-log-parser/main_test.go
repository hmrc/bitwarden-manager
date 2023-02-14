package main

import (
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestReadCSV(t *testing.T) {

	p := filepath.Join("testdata", "bitwarden_org-events_export.csv")
	records, err := readCSV(p)
	assert.Nil(t, err)

	expected := 17
	assert.Equal(t, expected, len(records))
}

func TestDailyLoginsCount(t *testing.T) {
	expected := map[string]int{"2023-01-09": 2, "2023-01-10": 1, "2023-01-26": 1, "2023-02-06": 1, "2023-02-07": 1}

	p := filepath.Join("testdata", "bitwarden_org-events_export.csv")
	records, _ := readCSV(p)
	got := dailyLoginsCount(records)
	assert.Equal(t, expected, got)
}

func TestAverageDailyLogins(t *testing.T) {
	p := filepath.Join("testdata", "bitwarden_org-events_export.csv")
	records, _ := readCSV(p)

	testCases := []struct {
		desc     string
		num      int
		expected float64
	}{
		{
			desc:     "last 5 days",
			num:      5,
			expected: 1.2,
		},
		{
			desc:     "last 3 days",
			num:      3,
			expected: 1,
		},
	}
	for _, tC := range testCases {
		t.Run(tC.desc, func(t *testing.T) {
			got := averageDailyLogins(records, tC.num)
			assert.Equal(t, tC.expected, got)
		})
	}
}

func TestDailyUniqueUserLoginsCount(t *testing.T) {
	expected := map[string]int{"2023-01-09": 1, "2023-01-10": 1, "2023-01-26": 1, "2023-02-06": 1, "2023-02-07": 1}

	p := filepath.Join("testdata", "bitwarden_org-events_export.csv")
	records, _ := readCSV(p)
	got := dailyUniqueUserLoginsCount(records)
	assert.Equal(t, expected, got)
}

func TestAverageDailyUniqueUserLogins(t *testing.T) {
	p := filepath.Join("testdata", "bitwarden_org-events_export.csv")
	records, _ := readCSV(p)

	testCases := []struct {
		desc     string
		num      int
		expected float64
	}{
		{
			desc:     "last 5 days",
			num:      5,
			expected: 1.2,
		},
		{
			desc:     "last 3 days",
			num:      3,
			expected: 1,
		},
	}
	for _, tC := range testCases {
		t.Run(tC.desc, func(t *testing.T) {
			// Changeme
			got := averageDailyLogins(records, tC.num)
			assert.Equal(t, tC.expected, got)
		})
	}
}
