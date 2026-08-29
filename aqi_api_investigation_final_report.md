# Ho Chi Minh City AQI API Investigation - Final Report
**Date**: August 20, 2026
**URLs Investigated**: 
- https://thongtinquantrac.moitruonghcm.vn/aqi
- https://thongtinquantrac.moitruonghcm.vn/en/aqi

## Executive Summary
Investigated the Ho Chi Minh City Environmental Information Portal's AQI system to identify API endpoints and data availability. **Result: PM2.5 concentration data NOT accessible through public APIs. Multiple endpoints are non-functional or protected.**

---

## Network Requests Captured

### 1. **FAILING**: /api/aqi-share
```
URL: https://thongtinquantrac.moitruonghcm.vn/api/aqi-share
Method: GET
Status: 500 Internal Server Error
Response:
{
  "success": false,
  "message": "Failed to fetch /..."
}
```
**PM2.5 Data**: ❌ NOT AVAILABLE - Endpoint returning server error

---

### 2. **WORKING**: /api/weather/newest-data  
```
URL: https://thongtinquantrac.moitruonghcm.vn/api/weather/newest-data
Method: GET
Status: 200 OK
Response Sample:
{
  "city": "Ho Chi Minh City",
  "data": [
    {
      "code": 802,
      "description": "Scattered Clouds",
      "icon": "[[INDEX]]",
      "url": "https://www.weatherbit.io/static/img/icons/c02d.png"
    }
  ],
  "parameters": [
    {"key": "temp", "label": "Temperature", ...},
    {"key": "wind_spd", "value": 7, ...},
    {"key": "rh", "value": 79, ...}
  ]
}
```
**PM2.5 Data**: ❌ NO - This is weather data (temperature, wind, humidity) NOT air quality

---

### 3. **REDIRECTED**: Station JSON Files
```
URLs Attempted:
- https://thongtinquantrac.moitruonghcm.vn/localres/en/aqi/aqiStations.json
- https://thongtinquantrac.moitruonghcm.vn/localres/en/aqi/wqiStations.json

Status: 302 Found → Redirects to 404 Page
Issue: Files appear in network log but are immediately redirected
```
**PM2.5 Data**: ❌ INACCESSIBLE - Cannot retrieve actual JSON content

---

### 4. **CONFIGURED BUT INACCESSIBLE**: airlotus-api.ilotusland.com
```
Discovered in page source (window.__ENV__):
{
  "AQI_API_URL": "https://airlotus-api.ilotusland.com",
  "WQI_API_URL": "http://113.190.254.225:5300",
  "MAIN_API_PUBLIC_URL": "https://api-thongtinquantrac.moitruonghcm.vn"
}

Endpoints Tested:
✗ https://airlotus-api.ilotusland.com/ → 404
✗ https://airlotus-api.ilotusland.com/stations → 404
✗ https://airlotus-api.ilotusland.com/api/stations → 404
✗ https://airlotus-api.ilotusland.com/api/v1/stations → 404
```
**PM2.5 Data**: ❌ CANNOT ACCESS - All endpoints return 404

---

### 5. **CMS BACKEND**: api-thongtinquantrac.moitruonghcm.vn
```
Platform: Strapi CMS (Headless CMS)
Base URL: https://api-thongtinquantrac.moitruonghcm.vn/
Status: Returns Strapi welcome page

Endpoints Tested:
✗ /stations → 404
✗ /aqi-stations → 404

Note: Strapi typically requires knowing exact content-type names
```
**PM2.5 Data**: ❌ UNKNOWN - Cannot determine without API documentation

---

## User Interaction Testing

### Map Station Markers
- **Status**: ❌ NO VISIBLE MARKERS
- **Observation**: Map loads and displays Ho Chi Minh City geography
- **Issue**: No clickable AQI station indicators appear on the map
- **Result**: Unable to trigger station detail panels or history chart API calls

### Historical Data Tabs
- **Status**: ❌ COULD NOT TEST
- **Reason**: No station detail panels opened (no markers to click)
- **Expected**: Hourly/Daily/Monthly tabs would trigger additional API calls
- **Actual**: Could not reach this functionality

---

## JSON Data Structure - NOT OBTAINED

Unable to provide JSON excerpts showing:
- ❌ Station keys/IDs
- ❌ Station names
- ❌ Latitude/Longitude coordinates
- ❌ PM2.5 vs AQI field mappings
- ❌ Timestamp formats
- ❌ Temporal granularity (hourly/daily/monthly)

**Reason**: All endpoints either fail, redirect, or return non-AQI data

---

## Technical Findings

### API Architecture
1. **Frontend**: Next.js application (React-based)
2. **Backend CMS**: Strapi at api-thongtinquantrac.moitruonghcm.vn
3. **External AQI Service**: airlotus-api.ilotusland.com (configured but not publicly accessible)
4. **Static Assets**: Attempted to serve via /localres/ path but redirects to 404

### Request Patterns Observed
- Initial page load requests aqiStations.json and wqiStations.json (both 302 redirects)
- Weather data fetched successfully from /api/weather/newest-data
- AQI share endpoint called but returns 500 error
- No XHR requests to airlotus-api domain observed during page load

---

## Conclusions

### Working Endpoints ✓
1. `https://thongtinquantrac.moitruonghcm.vn/api/weather/newest-data` (Weather data only, NO AQI)

### Failing Endpoints ✗
1. `https://thongtinquantrac.moitruonghcm.vn/api/aqi-share` (500 Error)
2. `https://airlotus-api.ilotusland.com/*` (All paths return 404)
3. `/localres/en/aqi/*.json` (302 redirects to 404)

### PM2.5 Concentrations in Responses?
**❌ NO** - PM2.5 concentrations do NOT appear in any accessible API responses

---

## Blocking Issues

1. **Server Error**: The /api/aqi-share endpoint is broken (HTTP 500)
2. **Access Protection**: Station JSON files are behind redirects preventing direct access
3. **External API Unavailable**: airlotus-api.ilotusland.com does not respond to standard REST patterns
4. **No Public Documentation**: API structure is not documented for external access
5. **UI Non-Functional**: Map markers don't render, preventing interactive testing
6. **Authentication Unknown**: May require API keys, tokens, or session cookies not visible in browser

---

## Recommendations for Data Access

1. **Contact Site Administrators**: Request official API documentation or data export
2. **Check Alternative Sources**: Vietnam's Ministry of Natural Resources may have data feeds
3. **Monitor Network Traffic**: Use browser DevTools during peak hours when data might load
4. **Inspect Mobile App**: If Android/iOS app exists (IOS_APP_URL/ANDROID_APP_URL in config), it may use different endpoints
5. **Server-Side Analysis**: Direct server logs or database access would be needed for actual data structure

---

## Screenshot Evidence
- Network tab captured showing all requests (aqiStations.json with 302 status, aqi-share with 500 status)
- Map interface loaded but without visible station markers
- DevTools Sources panel showing multiple domains

---

## Final Answer to User Query

**Question**: Whether PM2.5 concentrations appear in responses?  
**Answer**: **NO** - PM2.5 concentrations do NOT appear in any accessible API endpoint responses. The /api/weather/newest-data returns only weather parameters (temperature, wind speed, humidity). The /api/aqi-share endpoint that might contain AQI data returns a 500 error. Station data files redirect to 404 pages. The external airlotus-api.ilotusland.com service is not accessible via standard HTTP requests.

