const express = require('express');
const app = express();
const API = 'http://localhost:3000/api';
try { app.listen(3000); } catch (e) {}
module.exports = app;
