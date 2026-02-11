# stack-analyzer-api-get-price-history

## Description

This Cloud Function fetches stock price history from BigQuery (`t_daily_price`).
It is designed to be lightweight and efficient, selecting only `date`, `close_price`, and `volume`.

## API Endpoint

`GET /api/price-history?code=<stock_code>&days=<days>`

## Parameters

- `code`: Stock code (e.g., "5208")
- `days`: Number of days to fetch (default: 90)
