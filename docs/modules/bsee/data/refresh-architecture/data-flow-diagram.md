# Enhanced Data Refresh Flow Diagram

## Complete System Flow

```mermaid
graph TB
    Start([Start: data_refresh_enhanced_test.py]) --> Config[Load data_refresh_enhanced.yml]
    Config --> CheckFlag{Check enhanced_refresh flag}
    
    CheckFlag -->|True| Enhanced[DataRefreshEnhanced class]
    CheckFlag -->|False| Legacy[Legacy data_refresh.py]
    
    Enhanced --> CheckSources{Check enabled<br/>data sources}
    
    CheckSources -->|well: true| WellFlow[Process Well Data]
    CheckSources -->|production: true| ProdFlow[Process Production Data]
    CheckSources -->|war: true| WARFlow[Process WAR Data]
    
    %% Well Data Flow
    WellFlow --> WellScraper[BSEEWebScraper<br/>download_data('well')]
    WellScraper --> WellURL[GET: APDRawData.zip<br/>Timeout: 600s]
    WellURL --> WellMemory[MemoryProcessor<br/>process_zip_in_memory()]
    WellMemory --> WellChunk{File > 100MB?}
    WellChunk -->|Yes| WellChunkMgr[ChunkManager<br/>create_chunks()]
    WellChunk -->|No| WellOptimize[OptimizedProcessor<br/>optimize_dataframe()]
    WellChunkMgr --> WellOptimize
    WellOptimize --> WellSave[Save to .bin<br/>data/modules/bsee/bin/well/]
    
    %% Production Data Flow
    ProdFlow --> ProdScraper[BSEEWebScraper<br/>download_data('production')]
    ProdScraper --> ProdURL[GET: ProductionRawData.zip<br/>Timeout: 1200s]
    ProdURL --> ProdMemory[MemoryProcessor<br/>process_zip_in_memory()]
    ProdMemory --> ProdChunk{File > 100MB?}
    ProdChunk -->|Yes| ProdChunkMgr[ChunkManager<br/>create_chunks()]
    ProdChunk -->|No| ProdOptimize[OptimizedProcessor<br/>optimize_dataframe()]
    ProdChunkMgr --> ProdOptimize
    ProdOptimize --> ProdSave[Save to .bin<br/>data/modules/bsee/bin/production/]
    
    %% WAR Data Flow
    WARFlow --> WARScraper[BSEEWebScraper<br/>download_data('war')]
    WARScraper --> WARURL[GET: eWellWARRawData.zip<br/>Timeout: 2400s]
    WARURL --> WARMemory[MemoryProcessor<br/>process_zip_in_memory()]
    WARMemory --> WARChunk{File > 100MB?}
    WARChunk -->|Yes| WARChunkMgr[ChunkManager<br/>create_chunks()]
    WARChunk -->|No| WAROptimize[OptimizedProcessor<br/>optimize_dataframe()]
    WARChunkMgr --> WAROptimize
    WAROptimize --> WARSave[Save to .bin<br/>data/modules/bsee/bin/war/]
    
    %% Convergence
    WellSave --> Complete([Complete])
    ProdSave --> Complete
    WARSave --> Complete
    Legacy --> LegacyComplete([Legacy Complete])
    
    style Enhanced fill:#90EE90
    style WellFlow fill:#87CEEB
    style ProdFlow fill:#FFB6C1
    style WARFlow fill:#DDA0DD
    style Complete fill:#98FB98
```

## Detailed Module Interaction Flow

```mermaid
sequenceDiagram
    participant Test as data_refresh_enhanced_test.py
    participant Config as config_router.py
    participant Main as data_refresh_enhanced.py
    participant Scraper as web_scraper.py
    participant Memory as memory_processor.py
    participant Chunk as chunk_manager.py
    participant Optimize as optimized_processor.py
    participant Output as Binary Files (.bin)
    
    Test->>Config: Load configuration
    Config->>Config: Check enhanced_refresh flag
    Config->>Main: Initialize DataRefreshEnhanced
    
    loop For each enabled data source
        Main->>Scraper: Request data download
        Scraper->>Scraper: Check connectivity
        Scraper->>Scraper: Download with timeout
        Note over Scraper: Retry on failure (3x)
        Scraper-->>Main: Return ZIP content (bytes)
        
        Main->>Memory: Process ZIP in memory
        Memory->>Memory: Extract files from ZIP
        Memory->>Memory: Convert to DataFrame
        
        alt File size > 100MB
            Memory->>Chunk: Split into chunks
            Chunk->>Chunk: Process each chunk
            Chunk->>Optimize: Optimize chunk
            Optimize-->>Chunk: Return optimized
            Chunk-->>Memory: Return merged result
        else File size <= 100MB
            Memory->>Optimize: Optimize DataFrame
            Optimize-->>Memory: Return optimized
        end
        
        Memory->>Output: Save as .bin file
        Output-->>Main: Confirm save
    end
    
    Main-->>Test: Process complete
```

## Error Handling Flow

```mermaid
graph TD
    Operation[Any Operation] --> TryBlock{Try Block}
    
    TryBlock -->|Success| Continue[Continue Processing]
    TryBlock -->|Network Error| NetworkRetry{Retry Counter}
    TryBlock -->|Memory Error| MemoryHandler[Switch to Chunked Mode]
    TryBlock -->|Data Error| DataValidation[Validate & Clean]
    TryBlock -->|Other Error| LogError[Log Error Details]
    
    NetworkRetry -->|< 3| BackOff[Exponential Backoff]
    NetworkRetry -->|>= 3| FailNetwork[Fail with Network Error]
    BackOff --> TryBlock
    
    MemoryHandler --> ChunkedProcess[Process in Chunks]
    ChunkedProcess --> Continue
    
    DataValidation -->|Recoverable| CleanData[Clean Data]
    DataValidation -->|Unrecoverable| FailData[Fail with Data Error]
    CleanData --> Continue
    
    LogError --> FailGeneric[Fail with Generic Error]
    
    Continue --> NextOperation[Next Operation]
    FailNetwork --> ErrorReport[Generate Error Report]
    FailData --> ErrorReport
    FailGeneric --> ErrorReport
    
    style Continue fill:#90EE90
    style ErrorReport fill:#FFB6C1
```

## Configuration Router Decision Flow

```mermaid
graph TD
    Start[Read YAML Config] --> ParseYAML[Parse Configuration]
    ParseYAML --> CheckEnhanced{enhanced_refresh<br/>flag exists?}
    
    CheckEnhanced -->|Yes| CheckEnhancedValue{enhanced_refresh<br/>= true?}
    CheckEnhanced -->|No| CheckLegacy{refresh flag<br/>exists?}
    
    CheckEnhancedValue -->|Yes| UseEnhanced[Use Enhanced System]
    CheckEnhancedValue -->|No| CheckLegacy
    
    CheckLegacy -->|Yes| CheckLegacyValue{refresh = true?}
    CheckLegacy -->|No| NoOperation[No Refresh Operation]
    
    CheckLegacyValue -->|Yes| UseLegacy[Use Legacy System]
    CheckLegacyValue -->|No| NoOperation
    
    UseEnhanced --> ImportEnhanced[Import data_refresh_enhanced]
    UseLegacy --> ImportLegacy[Import data_refresh]
    
    ImportEnhanced --> ExecuteEnhanced[Execute Enhanced Refresh]
    ImportLegacy --> ExecuteLegacy[Execute Legacy Refresh]
    
    style UseEnhanced fill:#90EE90
    style UseLegacy fill:#FFD700
    style NoOperation fill:#D3D3D3
```

## Memory Processing Flow

```mermaid
graph LR
    ZipBytes[ZIP Bytes<br/>from Scraper] --> BytesIO[io.BytesIO<br/>wrapper]
    BytesIO --> ZipFile[zipfile.ZipFile<br/>object]
    
    ZipFile --> Extract{Extract Each File}
    
    Extract --> FileContent[File Content<br/>in Memory]
    FileContent --> Decode[Decode to Text]
    Decode --> Parse[Parse CSV/TSV]
    Parse --> DataFrame[Pandas DataFrame]
    
    DataFrame --> Optimize[Optimize Types]
    Optimize --> Pickle[Pickle Serialize]
    Pickle --> BinFile[.bin File]
    
    BinFile --> SavePath[data/modules/bsee/bin/{type}/]
    
    style ZipBytes fill:#87CEEB
    style DataFrame fill:#90EE90
    style BinFile fill:#FFD700
```

## Parallel Processing Architecture

```mermaid
graph TD
    Config[Configuration] --> Parallel{Parallel<br/>Execution?}
    
    Parallel -->|Yes| ThreadPool[ThreadPoolExecutor]
    Parallel -->|No| Sequential[Sequential Processing]
    
    ThreadPool --> WellThread[Well Data Thread]
    ThreadPool --> ProdThread[Production Thread]
    ThreadPool --> WARThread[WAR Data Thread]
    
    WellThread --> WellProcess[Process Well Data]
    ProdThread --> ProdProcess[Process Production]
    WARThread --> WARProcess[Process WAR Data]
    
    Sequential --> ProcessOne[Process Well]
    ProcessOne --> ProcessTwo[Process Production]
    ProcessTwo --> ProcessThree[Process WAR]
    
    WellProcess --> Merge[Merge Results]
    ProdProcess --> Merge
    WARProcess --> Merge
    ProcessThree --> SeqComplete[Complete]
    
    Merge --> ParComplete[Complete]
    
    style ThreadPool fill:#87CEEB
    style Merge fill:#90EE90
    style ParComplete fill:#98FB98
    style SeqComplete fill:#98FB98
```

## Test Execution Flow

```mermaid
graph TD
    TestStart[python data_refresh_enhanced_test.py] --> LoadTest[Load Test Configuration]
    LoadTest --> SetupEnv[Setup Test Environment]
    
    SetupEnv --> MockCheck{Mock Mode?}
    MockCheck -->|Yes| MockData[Use Mock Data]
    MockCheck -->|No| LiveData[Use Live BSEE Data]
    
    MockData --> RunTests[Run Test Suite]
    LiveData --> RunTests
    
    RunTests --> UnitTests[Unit Tests]
    RunTests --> IntegrationTests[Integration Tests]
    RunTests --> CompatTests[Compatibility Tests]
    
    UnitTests --> TestResults[Collect Results]
    IntegrationTests --> TestResults
    CompatTests --> TestResults
    
    TestResults --> Report[Generate Test Report]
    Report --> Success{All Pass?}
    
    Success -->|Yes| PassNotify[✅ Tests Passed]
    Success -->|No| FailNotify[❌ Tests Failed]
    
    style PassNotify fill:#90EE90
    style FailNotify fill:#FFB6C1
```

## Data Type Processing Specifics

```mermaid
graph TD
    DataType{Data Type} --> Well[Well/APD Data]
    DataType --> Prod[Production Data]
    DataType --> WAR[WAR Data]
    
    Well --> WellURL[APDRawData.zip]
    WellURL --> WellTimeout[Timeout: 600s]
    WellTimeout --> WellSize[Size: ~5MB]
    WellSize --> WellFreq[Update: Daily]
    
    Prod --> ProdURL[ProductionRawData.zip]
    ProdURL --> ProdTimeout[Timeout: 1200s]
    ProdTimeout --> ProdSize[Size: ~15MB]
    ProdSize --> ProdFreq[Update: Bi-monthly]
    
    WAR --> WARURL[eWellWARRawData.zip]
    WARURL --> WARTimeout[Timeout: 2400s]
    WARTimeout --> WARSize[Size: ~120MB]
    WARSize --> WARFreq[Update: Daily]
    
    WellFreq --> Process[Standard Processing]
    ProdFreq --> Process
    WARFreq --> ChunkedProc[Chunked Processing]
    
    style Well fill:#87CEEB
    style Prod fill:#FFB6C1
    style WAR fill:#DDA0DD
```

## Notes

- All flows are designed to be **idempotent** - can be run multiple times safely
- **Parallel processing** is used where possible to improve performance
- **Memory management** is critical for large files (especially WAR data)
- **Error recovery** is built into every step of the process
- **Binary compatibility** is maintained with legacy system outputs