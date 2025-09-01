# Prompt Documentation

> Spec: Web API Integration for Data Procurement
> Created: 2025-09-01

## Original User Prompt

```
/create-spec module data procurement 

Research if web apis exist to avoid downloading the data on to the repo. If yes, write tests
```

## Prompt Analysis

### Key Requirements Identified
1. **Module Focus**: Data procurement system
2. **Primary Goal**: Avoid downloading data to repository
3. **Research Component**: Investigate existing web APIs
4. **Testing Requirement**: Write comprehensive tests for API integrations

### Context Understanding
- Repository contains existing BSEE data scrapers and file-based data processing
- Current approach downloads large ZIP files which causes repository bloat
- Need to transition from file-based to API-based data access
- Testing is critical for reliability of external data sources

## Research Findings

### Existing Codebase Analysis
1. **Current Implementation**: 
   - BSEEWebScraper class downloads ZIP files to memory
   - Multiple data sources: well, production, WAR data
   - File-based processing throughout the codebase

2. **API Research Conducted**:
   - Found evidence of ArcGIS REST services for BOEM/BSEE spatial data
   - Discovered web-based query interfaces with potential AJAX endpoints
   - Identified government API patterns in test files

3. **Available Data Sources**:
   - **BSEE**: Production, well, lease, block data (currently file-based)
   - **EIA**: Energy Information Administration has documented REST APIs
   - **NOAA**: Weather and ocean data APIs available
   - **ArcGIS**: Spatial data services for offshore locations

## Design Decisions

### Architecture Choices
1. **Universal API Client**: Single configurable client for all API types
2. **Transformation Pipeline**: Convert diverse formats to internal schema
3. **Multi-tier Caching**: Memory + Redis for performance and resilience
4. **Configuration-Driven**: Add new APIs without code changes

### Technical Approach
- Use existing requests library with enhanced retry logic
- Implement circuit breaker pattern for API failures
- Cache responses with intelligent TTL strategies
- Transform all data to pandas DataFrames for consistency

## Curated Reuse Prompt

For future enhancements or similar API integration tasks, use this optimized prompt:

```
Create a web API integration module for [DATA_SOURCE] that:
1. Discovers and documents available REST/GraphQL/SOAP endpoints
2. Implements authenticated API client with retry logic and rate limiting
3. Transforms responses to standardized internal format (pandas DataFrame)
4. Includes multi-tier caching (memory + Redis) with TTL strategies
5. Provides fallback mechanisms for API failures
6. Writes comprehensive integration tests with recorded responses
7. Uses configuration files for API endpoints, not hardcoded values
8. Monitors API health and provides metrics/alerts

Focus on these government/industry APIs:
- [List specific APIs like BSEE, EIA, NOAA]

Ensure the solution:
- Eliminates need for downloading/storing large files
- Handles authentication (API key, OAuth, Basic)
- Respects rate limits with backoff strategies
- Provides offline capability through caching
```

## Implementation Notes

### Priority Order
1. BSEE APIs (core business data)
2. EIA APIs (energy statistics)
3. NOAA APIs (weather impacts)
4. Other industry APIs

### Testing Strategy
- Unit tests with mocked responses
- Integration tests with recorded real responses
- Performance tests for cache efficiency
- Resilience tests for API failures

### Performance Targets
- 95% cache hit rate for repeated queries
- &lt;500ms response time for cached data
- Automatic retry with exponential backoff
- Circuit breaker activates after 3 consecutive failures

## Next Steps

After spec approval:
1. Start with API discovery and documentation
2. Build universal client framework
3. Implement BSEE integration first
4. Add other sources incrementally
5. Deploy with monitoring and alerting