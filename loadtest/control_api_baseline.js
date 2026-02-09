import http from 'k6/http';
import { sleep } from 'k6';


export const options = {
  vus: 50, // users count
  duration: '2m',
};

export default function () {
  http.get('http://localhost/healthz');
  sleep(1);
}
