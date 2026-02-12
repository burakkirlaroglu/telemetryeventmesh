import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 20,
  duration: '30s',
};

const API_KEY = 'api-key';

export default function () {
  const payload = JSON.stringify(
  {
    source: "service-a",
    event_type: "cpu.usage",
    timestamp: "2026-02-10T10:15:30Z",
    payload: {"value": 73.4}
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  };

  const res = http.post(
    'http://localhost:8002/api/events/',
    payload,
    params
  );

  check(res, {
    'status is 202': (r) => r.status === 202,
  });

  sleep(0);
}
