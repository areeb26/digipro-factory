# Review Dashboard

A comprehensive Flask web application for reviewing, approving, and managing digital products before publishing to marketplaces.

## Features

- **Product Review Grid**: Visual dashboard showing all pending products with thumbnails
- **Detailed Product View**: Complete product information with marketing content
- **Approve/Edit/Reject Workflow**: Interactive buttons with confirmation modals
- **Statistics Dashboard**: Performance metrics with Chart.js visualizations
- **File Management**: Download PDFs, images, and data files
- **CSRF Protection**: Secure forms with Flask-WTF
- **RESTful API**: JSON endpoints for integration
- **Responsive UI**: Bootstrap 5 with mobile-first design

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize the database:
```bash
python app.py
# Database will be initialized automatically on first run
```

## Usage

### Running the Server

**Development Mode:**
```bash
cd review_dashboard
flask --app app run --debug
```

or

```bash
python app.py
```

The dashboard will be accessible at `http://localhost:5000`

**Production Mode:**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Environment Variables

Add to `.env` file:

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

# Optional: Override default database path
DATABASE_PATH=data/products.db
```

## Routes

### Web Interface

- `GET /` - Product review dashboard (grid view)
- `GET /product/<id>` - Detailed product view
- `GET /stats` - Statistics dashboard with charts
- `GET /download/<id>/<filename>` - Download product files

### API Endpoints

- `POST /approve/<id>` - Approve a product
  ```json
  Response: {"success": true, "product_id": 1, "new_status": "approved"}
  ```

- `POST /edit/<id>` - Edit product data
  ```json
  Request: {
    "title": "New Title",
    "description": "Updated description",
    "price": 15.00,
    "niche": "productivity",
    "type": "planner",
    "edit_reason": "Fixed typo in title"
  }
  Response: {"success": true, "product_id": 1, "updated_fields": ["title"]}
  ```

- `POST /reject/<id>` - Reject a product
  ```json
  Request: {"reason": "Quality does not meet standards"}
  Response: {"success": true, "product_id": 1, "new_status": "archived"}
  ```

- `GET /api/products` - Get all pending products
  ```json
  Response: {
    "success": true,
    "products": [...],
    "count": 10
  }
  ```

- `GET /api/product/<id>` - Get product details
  ```json
  Response: {
    "success": true,
    "product": {...},
    "marketing": {...}
  }
  ```

- `GET /health` - Health check endpoint
  ```json
  Response: {"status": "healthy", "timestamp": "2025-11-13T21:00:00"}
  ```

## Security Features

### CSRF Protection
All POST endpoints are protected with CSRF tokens via Flask-WTF. The token is automatically included in AJAX requests using the `fetchWithCSRF()` helper function.

### Session Security
- HttpOnly cookies prevent XSS attacks
- SameSite=Lax prevents CSRF attacks
- Secure cookies in production (HTTPS)

### Input Validation
- Parameterized database queries prevent SQL injection
- Filename sanitization for downloads
- File type whitelist for security

### File Download Security
- Only allowed extensions: pdf, png, jpg, jpeg, json, txt, csv
- Filename sanitization with `secure_filename()`
- File path validation to prevent directory traversal

## User Interface

### Dashboard (/)
- Grid layout showing pending products
- Thumbnail images or placeholder icons
- Product title, type, niche, and price
- Created date for each product
- "Review" button linking to detailed view

### Product Detail (/product/<id>)
- **Action Buttons**: Approve (green), Edit (yellow), Reject (red)
- **Product Information**: All metadata in clean table format
- **Marketing Content**: Accordion view organized by platform (Etsy, Instagram, Facebook, etc.)
- **Files Section**: Categorized downloads (PDFs, images, data files)
- **Listings**: Published listings with views, sales, and revenue

### Statistics Dashboard (/stats)
- **Key Metrics Cards**: Total products, active listings, views, sales
- **Revenue Metrics**: Total revenue, conversion rate, average order value
- **Chart Visualizations**: Product status distribution (doughnut chart)
- **Top Performers**: Best-selling products table
- **Recent Activity**: Latest products added
- **Trending Keywords**: Top trends by demand score

### Modals
- **Edit Modal**: Form with all editable fields + edit reason
- **Reject Modal**: Textarea for rejection reason + warning message

## Database Integration

The dashboard uses the ProductDB class from `database.py`:

```python
from database import ProductDB

db = ProductDB()

# Get pending products
products = db.get_pending_products(limit=100)

# Update product status
db.update_product_status(product_id, 'approved')

# Get statistics
stats = db.get_stats()
```

## Error Handling

### Custom Error Pages
- **404 Not Found**: Clean error page with navigation options
- **500 Internal Server Error**: User-friendly error message with logging

### Flash Messages
- Success messages (green)
- Error messages (red)
- Info messages (blue)
- Warning messages (yellow)

## Logging

All actions are logged:
- Product approvals
- Product edits with reasons
- Product rejections with reasons (also saved to `rejections.log`)
- File downloads
- API requests
- Errors with stack traces

## Customization

### Styling
Edit CSS variables in `templates/base.html`:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    --success-color: #10b981;
    --danger-color: #ef4444;
    --warning-color: #f59e0b;
}
```

### Templates
All templates extend `base.html`:
- `index.html` - Dashboard grid
- `product_detail.html` - Product review page
- `stats.html` - Statistics dashboard
- `error.html` - Error pages

## CLI Commands

```bash
# Initialize database
flask --app app init-db

# Run development server
flask --app app run-dev
```

## Production Deployment

1. Set proper environment variables:
```bash
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_ENV=production
export SESSION_COOKIE_SECURE=True
```

2. Use a production WSGI server:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. Use a reverse proxy (nginx/Apache):
```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

4. Enable HTTPS for secure cookies

## Testing

### Manual Testing
1. Create test products in the database
2. Access dashboard at http://localhost:5000
3. Review products and test approve/edit/reject
4. Check statistics dashboard
5. Verify file downloads

### API Testing
```bash
# Health check
curl http://localhost:5000/health

# Get products
curl http://localhost:5000/api/products

# Get product detail
curl http://localhost:5000/api/product/1
```

## Troubleshooting

### Database Errors
- Ensure database file has write permissions
- Check `data/` directory exists
- Verify `database.py` is accessible

### CSRF Errors
- Ensure CSRF token meta tag is in templates
- Verify `Flask-WTF` is installed
- Check browser allows cookies

### File Download Issues
- Verify `file_path` in product database
- Check file exists at specified path
- Ensure file extension is in whitelist

## Architecture

```
review_dashboard/
├── app.py                 # Main Flask application
├── templates/             # Jinja2 templates
│   ├── base.html         # Base layout
│   ├── index.html        # Dashboard grid
│   ├── product_detail.html  # Product review
│   ├── stats.html        # Statistics
│   └── error.html        # Error pages
├── rejections.log        # Rejection reasons log
└── README.md             # This file
```

## Dependencies

- Flask 3.1.0 - Web framework
- Flask-WTF 1.2.1 - CSRF protection
- Bootstrap 5.3.0 - UI framework (CDN)
- Chart.js 4.4.0 - Visualizations (CDN)
- Bootstrap Icons - Icon library (CDN)

## License

Part of Digital Product Factory project.

## Support

For issues or questions, check the logs in the console or contact the development team.
