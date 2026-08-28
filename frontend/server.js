require('dotenv').config({ path: '../.env' });
const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Expose API URL to frontend via config endpoint
app.get('/config', (req, res) => {
    res.json({
        apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8000'
    });
});

app.use(express.static(__dirname));

app.listen(port, () => {
    console.log(`Service run on http://localhost:${port}`);
});
