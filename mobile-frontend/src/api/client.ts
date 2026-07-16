import axios from 'axios';

// Ensure this matches the Laravel backend base URL
// Use your local IP address instead of localhost if running on a physical device.
// e.g., 'http://192.168.1.100:8000/api'
const BASE_URL = 'http://10.0.2.2:8000/api';

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

export default apiClient;
