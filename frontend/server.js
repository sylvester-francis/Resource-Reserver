const express = require('express');
const path = require('path');
const axios = require('axios');
const cookieParser = require('cookie-parser');
const luxon = require('luxon');
const multer = require('multer');

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Configure multer for file uploads
const upload = multer({ dest: 'uploads/' });

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Set EJS as templating engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// API helper function
async function apiCall(endpoint, options = {}, token = null) {
  try {
    const config = {
      baseURL: API_BASE_URL,
      url: endpoint,
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers
      }
    };

    const response = await axios(config);
    return response.data;
  } catch (error) {
    if (error.response) {
      // Extract meaningful error messages from backend
      const errorMessage = error.response.data.detail ||
        error.response.data.message ||
        error.response.data.error ||
        `Service error (${error.response.status})`;
      throw new Error(errorMessage);
    }
    throw new Error('Unable to connect to the server. Please check your connection.');
  }
}

// Authentication middleware with token validation
async function requireAuth(req, res, next) {
  const token = req.cookies.auth_token;

  if (!token) {
    return res.redirect('/login?error=' + encodeURIComponent('Please log in to access this page'));
  }

  try {
    // Validate token with backend by making a test API call to a protected endpoint
    await apiCall('/reservations/my', { method: 'GET' }, token);
    req.token = token;
    next();
  } catch (error) {
    // Token is invalid/expired, clear cookies and redirect to login
    res.clearCookie('auth_token');
    res.clearCookie('username');
    return res.redirect('/login?error=' + encodeURIComponent('Your session has expired. Please log in again.'));
  }
}

// Routes
app.get('/', async (req, res) => {
  const token = req.cookies.auth_token;
  if (token) {
    // Validate token before redirecting to dashboard
    try {
      await apiCall('/reservations/my', { method: 'GET' }, token);
      res.redirect('/dashboard');
    } catch (error) {
      // Token is invalid/expired, clear cookies and redirect to login
      res.clearCookie('auth_token');
      res.clearCookie('username');
      res.redirect('/login?error=' + encodeURIComponent('Your session has expired. Please log in again.'));
    }
  } else {
    res.redirect('/login');
  }
});

app.get('/login', (req, res) => {
  res.render('login', {
    title: 'Login - Resource Reservation System',
    error: req.query.error,
    success: req.query.success
  });
});

app.get('/register', (req, res) => {
  // Redirect to login page which has both login and register forms
  res.redirect('/login?success=' + encodeURIComponent(req.query.success || ''));
});

app.post('/auth/login', async (req, res) => {
  try {
    const formData = new URLSearchParams();
    formData.append('username', req.body.username);
    formData.append('password', req.body.password);

    const response = await axios.post(`${API_BASE_URL}/token`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    res.cookie('auth_token', response.data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'Lax', // Required for Safari compatibility
      maxAge: 24 * 60 * 60 * 1000 // 24 hours
    });

    res.cookie('username', req.body.username, {
      sameSite: 'Lax', // Required for Safari compatibility
      maxAge: 24 * 60 * 60 * 1000
    });

    res.redirect('/dashboard');
  } catch (error) {
    res.redirect('/login?error=' + encodeURIComponent(error.message));
  }
});

app.post('/auth/register', async (req, res) => {
  try {
    await apiCall('/register', {
      method: 'POST',
      data: {
        username: req.body.username,
        password: req.body.password
      }
    });

    res.redirect('/login?success=Registration successful! Please log in.');
  } catch (error) {
    res.redirect('/register?error=' + encodeURIComponent(error.message));
  }
});

app.post('/auth/logout', (req, res) => {
  res.clearCookie('auth_token');
  res.clearCookie('username');
  res.redirect('/login');
});

app.get('/dashboard', requireAuth, async (req, res) => {
  try {
    console.log('Dashboard loading...');
    const [resources, reservations, systemStatus] = await Promise.all([
      apiCall('/resources/search?status=available', { method: 'GET' }, req.token),
      apiCall('/reservations/my', { method: 'GET' }, req.token),
      apiCall('/health', { method: 'GET' })
    ]);
    console.log('Dashboard data loaded:', {
      resourceCount: resources.length,
      reservationCount: reservations.length
    });

    // Get total count from health endpoint or make separate call
    const totalResourcesResponse = await apiCall('/resources/search?status=all', { method: 'GET' }, req.token);

    const stats = {
      totalResources: totalResourcesResponse.length,
      availableResources: resources.length, // Since we filtered for available only
      activeReservations: reservations.filter(r => r.status === 'active').length,
      upcomingReservations: reservations.filter(r => r.status === 'active' && new Date(r.start_time) > new Date()).length
    };

    res.render('dashboard', {
      title: 'Dashboard - Resource Reservation System',
      username: req.cookies.username,
      resources,
      reservations,
      stats,
      systemStatus
    });
  } catch (error) {
    if (error.message.includes('401') || error.message.includes('Unauthorized')) {
      res.clearCookie('auth_token');
      res.redirect('/login?error=Session expired');
    } else {
      res.render('dashboard', {
        title: 'Dashboard - Resource Reservation System',
        username: req.cookies.username,
        resources: [],
        reservations: [],
        stats: { totalResources: 0, availableResources: 0, activeReservations: 0, upcomingReservations: 0 },
        systemStatus: null,
        error: error.message
      });
    }
  }
});

// API proxy routes
app.post('/api/resources', requireAuth, async (req, res) => {
  try {
    const result = await apiCall('/resources', {
      method: 'POST',
      data: req.body
    }, req.token);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/reservations', requireAuth, async (req, res) => {
  try {
    const result = await apiCall('/reservations', {
      method: 'POST',
      data: req.body
    }, req.token);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.delete('/api/reservations/:id', requireAuth, async (req, res) => {
  try {
    const result = await apiCall(`/reservations/${req.params.id}/cancel`, {
      method: 'POST',
      data: { reason: 'Cancelled by user' }
    }, req.token);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/resources/search', async (req, res) => {
  try {
    const result = await apiCall('/resources/search', {
      method: 'GET',
      params: req.query
    });
    // Return the result directly since backend returns the raw array
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/resources/availability/summary', async (req, res) => {
  try {
    const result = await apiCall('/resources/availability/summary', {
      method: 'GET'
    });
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/resources/:id/availability', async (req, res) => {
  try {
    const result = await apiCall(`/resources/${req.params.id}/availability`, {
      method: 'GET',
      params: req.query
    });
    // Return the result directly since the backend already returns {success: true, data: {...}}
    res.json(result);
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.put('/api/resources/:id/availability', requireAuth, async (req, res) => {
  try {
    const result = await apiCall(`/resources/${req.params.id}/availability`, {
      method: 'PUT',
      data: req.body
    }, req.token);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/reservations/:id/history', requireAuth, async (req, res) => {
  try {
    const result = await apiCall(`/reservations/${req.params.id}/history`, {
      method: 'GET'
    }, req.token);
    // Return the result directly since backend returns the raw array
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/admin/cleanup-expired', requireAuth, async (req, res) => {
  try {
    const result = await apiCall('/admin/cleanup-expired', {
      method: 'POST'
    }, req.token);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/upload', requireAuth, upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No file uploaded' });
    }

    const fs = require('fs');
    const FormData = require('form-data');

    const formData = new FormData();
    formData.append('file', fs.createReadStream(req.file.path), {
      filename: req.file.originalname,
      contentType: 'text/csv'
    });

    const response = await axios.post(`${API_BASE_URL}/resources/upload`, formData, {
      headers: {
        ...formData.getHeaders(),
        Authorization: `Bearer ${req.token}`
      }
    });

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    res.json({ success: true, data: response.data });
  } catch (error) {
    // Clean up uploaded file on error
    if (req.file && req.file.path) {
      try {
        require('fs').unlinkSync(req.file.path);
      } catch (cleanupError) {
        console.error('Error cleaning up file:', cleanupError);
      }
    }

    const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';
    res.status(400).json({ success: false, error: errorMessage });
  }
});

app.get('/api/health', async (req, res) => {
  try {
    const result = await apiCall('/health', {
      method: 'GET'
    });
    // Add timestamp to health data
    const healthData = {
      ...result,
      timestamp: new Date().toISOString()
    };
    res.json({ success: true, data: healthData });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend server running on http://localhost:${PORT}`);
  console.log(`Backend API URL: ${API_BASE_URL}`);
});