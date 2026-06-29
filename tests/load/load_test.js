import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    // 👉 Defining a realistic Facebook Traffic Wave
    stages: [
        { duration: '30s', target: 40 },  // Ramp up from 0 to 40 users quickly
        { duration: '1m', target: 120 },  // Surge up to 120 concurrent players (Peak Wave)
        { duration: '1m', target: 120 },  // Hold at 120 users to test stability & memory
        { duration: '30s', target: 0 },   // Ramp down smoothly back to 0
    ],
    thresholds: {
        // Guarantee that 95% of requests respond in under 500ms
        http_req_duration: ['p(95)<500'],
    },
};

export default function () {
    // 1. Hit the home page layout (Gets your optimized HTML structure)
    const homeRes = http.get('https://zambot.live/');
    check(homeRes, {
        'homepage status is 200': (r) => r.status === 200,
    });

    // Simulate a user reading the page for a brief moment
    sleep(Math.random() * 2 + 1);

    // 2. Fetch the JSON data stream from your FastAPI background engine
    const dataRes = http.get('https://zambot.live/sessions');
    check(dataRes, {
        'sessions payload is 200': (r) => r.status === 200,
    });

    // Pause before the next virtual loop iteration
    sleep(Math.random() * 3 + 1);
}
