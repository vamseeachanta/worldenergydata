# Framework wrapper for drilling and completion days analysis
# This class integrates the existing drilling analysis logic with the worldenergydata framework

import pandas as pd
import pickle
import os
from loguru import logger


class DrillingCompletionDays:
    """
    Framework wrapper class for drilling and completion days analysis.
    
    This class provides a framework-compatible interface to the existing
    drilling and completion days analysis logic while maintaining all
    original functionality.
    """
    
    def __init__(self):
        """Initialize the framework wrapper."""
        self.cfg = None
        self.lease_df = None
        self.leases = None
        self.lease_info = None
        self.main_war = None
        self.main_war_filtered = None
        self.boreholes = None
        self.main_prop = None
        
    def router(self, cfg):
        """
        Framework router method that processes the configuration and executes analysis.
        
        Args:
            cfg (dict): Configuration dictionary containing file paths and settings
        """
        self.cfg = cfg
        logger.info("Starting drilling and completion days analysis")
        
        try:
            # Load data from configured paths
            self._load_lease_data()
            self._load_war_data()
            self._process_analysis()
            logger.info("Analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
    
    def _resolve_path(self, file_path):
        """
        Resolve relative file paths to absolute paths.
        
        Args:
            file_path (str): The file path to resolve
            
        Returns:
            str: Resolved absolute path
        """
        if os.path.isabs(file_path):
            return file_path
            
        if os.path.exists(file_path):
            return os.path.abspath(file_path)
            
        # Try relative to current working directory and project root
        current_dir = os.path.dirname(__file__)
        # Find project root by looking for setup.py or pyproject.toml
        project_root = current_dir
        while project_root != os.path.dirname(project_root):  # Not at filesystem root
            if os.path.exists(os.path.join(project_root, 'pyproject.toml')) or os.path.exists(os.path.join(project_root, 'setup.py')):
                break
            project_root = os.path.dirname(project_root)
            
        search_paths = [os.getcwd(), project_root]
        
        for base_path in search_paths:
            full_path = os.path.join(base_path, file_path)
            logger.debug(f"Trying path: {full_path}")
            if os.path.exists(full_path):
                logger.info(f"Resolved path: {file_path} -> {full_path}")
                return full_path
                
        # If not found, return original path (will cause error if file doesn't exist)
        logger.warning(f"Could not resolve path: {file_path}. Tried: {search_paths}")
        return file_path
    
    def _load_lease_data(self):
        """Load lease data from configured CSV file."""
        lease_path = self.cfg.get('filepath', {}).get('leases', 'tests/modules/bsee/analysis/leases.csv')
        
        lease_path = self._resolve_path(lease_path)
        
        logger.info(f"Loading lease data from: {lease_path}")
        
        # Load lease list: Column A = LEASE_NAME, B = LEASE_NUM, C = WATER_DEPTH
        self.lease_df = pd.read_csv(lease_path, header=None, encoding="utf-8-sig", dtype=str)
        self.lease_df.columns = ['LEASE_NUM', 'LEASE_NAME', 'WATER_DEPTH']
        self.lease_df['LEASE_NUM'] = self.lease_df['LEASE_NUM'].str.upper().str.strip()
        self.lease_df = self.lease_df.dropna(subset=['LEASE_NUM'])
        self.leases = self.lease_df['LEASE_NUM'].str.replace('^G', '', regex=True).tolist()
        logger.info(f"Loaded {len(self.leases)} lease numbers from leases.csv (stripped of 'G')")
        
        # Build lease lookup dictionary
        self.lease_info = (
            self.lease_df.drop_duplicates(subset=['LEASE_NUM'])
            .assign(LEASE_NUM=lambda df: df['LEASE_NUM'].str.upper().str.replace('^G', '', regex=True).str.strip())
            .set_index('LEASE_NUM')[['LEASE_NAME', 'WATER_DEPTH']]
            .to_dict(orient='index')
        )
    
    def _load_war_data(self):
        """Load WAR data from configured binary files."""
        war_files = self.cfg.get('filepath', {}).get('war_files', {})
        
        # Load WAR main data
        main_path = war_files.get('main', 'data/modules/bsee/bin/war/mv_war_main.bin')
        main_path = self._resolve_path(main_path)
        logger.info(f"Loading main WAR data from: {main_path}")
        
        with open(main_path, 'rb') as f:
            self.main_war = pickle.load(f)
            
        logger.info(f"Loaded {len(self.main_war)} main WAR records")
        
        # Process main WAR data
        self.main_war['SURF_LEASE_NUM'] = self.main_war['SURF_LEASE_NUM'].astype(str).str.upper().str.replace('^G', '', regex=True).str.strip()
        self.main_war['API_WELL_NUMBER'] = self.main_war['API_WELL_NUMBER'].astype(str).str.zfill(10)
        self.main_war['SN_WAR'] = self.main_war['SN_WAR'].astype(str).str.strip()
        self.main_war['WELL_NAME'] = self.main_war['WELL_NAME'].fillna("")
        self.main_war['WAR_START_DT'] = pd.to_datetime(self.main_war['WAR_START_DT'], errors='coerce')
        self.main_war['WAR_END_DT'] = pd.to_datetime(self.main_war['WAR_END_DT'], errors='coerce')
        
        # Filter by lease
        self.main_war['SURF_LEASE_NUM'] = self.main_war['SURF_LEASE_NUM'].astype(str)
        self.main_war_filtered = self.main_war[self.main_war['SURF_LEASE_NUM'].isin(self.leases)].copy()
        logger.info(f"Filtered WAR records: {len(self.main_war_filtered)} out of {len(self.main_war)}")
        
        # Load boreholes data
        boreholes_path = war_files.get('boreholes', 'data/modules/bsee/bin/war/mv_war_boreholes_view.bin')
        boreholes_path = self._resolve_path(boreholes_path)
        logger.info(f"Loading boreholes data from: {boreholes_path}")
        
        with open(boreholes_path, 'rb') as f:
            self.boreholes = pickle.load(f)
            
        logger.info(f"Loaded {len(self.boreholes)} borehole records")
        
        # Process boreholes data
        self.boreholes['API_WELL_NUMBER'] = self.boreholes['API_WELL_NUMBER'].astype(str).str.zfill(10)
        self.boreholes['WELL_SPUD_DATE'] = pd.to_datetime(self.boreholes['WELL_SPUD_DATE'], errors='coerce')
        self.boreholes['TOTAL_DEPTH_DATE'] = pd.to_datetime(self.boreholes['TOTAL_DEPTH_DATE'], errors='coerce')
        self.boreholes['BH_TOTAL_MD'] = pd.to_numeric(self.boreholes['BH_TOTAL_MD'], errors='coerce')
        self.boreholes['WELL_BORE_TVD'] = pd.to_numeric(self.boreholes['WELL_BORE_TVD'], errors='coerce')
        
        # Load properties data
        prop_path = war_files.get('prop', 'data/modules/bsee/bin/war/mv_war_main_prop.bin')
        prop_path = self._resolve_path(prop_path)
        logger.info(f"Loading properties data from: {prop_path}")
        
        with open(prop_path, 'rb') as f:
            self.main_prop = pickle.load(f)
            
        logger.info(f"Loaded {len(self.main_prop)} property records")
        
        # Process properties data
        self.main_prop['SN_WAR'] = self.main_prop['SN_WAR'].astype(str).str.strip()
        self.main_prop['DRILL_FLUID_WGT'] = pd.to_numeric(self.main_prop['DRILL_FLUID_WGT'], errors='coerce')
    
    def _process_analysis(self):
        """Execute the drilling and completion days analysis."""
        logger.info("Processing drilling and completion days analysis")
        
        # Extract TD from boreholes
        td_from_boreholes = (
            self.boreholes.dropna(subset=['TOTAL_DEPTH_DATE'])
            .groupby('API_WELL_NUMBER')['TOTAL_DEPTH_DATE']
            .max()
            .reset_index()
        )
        
        # Add depth info
        depth_summary = self.boreholes.groupby('API_WELL_NUMBER')[['BH_TOTAL_MD', 'WELL_BORE_TVD']].max().reset_index()
        depth_summary.columns = ['API_WELL_NUMBER', 'MAX_BH_TOTAL_MD', 'MAX_WELL_BORE_TVD']
        
        # Merge API_WELL_NUMBER from main_war for properties
        main_merge = self.main_war[['SN_WAR', 'API_WELL_NUMBER']].dropna().drop_duplicates()
        main_merge['API_WELL_NUMBER'] = main_merge['API_WELL_NUMBER'].astype(str).str.zfill(10)
        self.main_prop = self.main_prop.merge(main_merge, on='SN_WAR', how='left')
        
        # Group to get max mud weight per API
        mud_summary = (
            self.main_prop.dropna(subset=['DRILL_FLUID_WGT'])
            .groupby('API_WELL_NUMBER')['DRILL_FLUID_WGT']
            .max()
            .reset_index()
            .rename(columns={'DRILL_FLUID_WGT': 'MAX_DRILL_FLUID_WGT'})
        )
        
        # Build drilling timeline
        GAP_THRESHOLD = 300
        
        def adjust_spud(api, td):
            war_dates = self.main_war_filtered[self.main_war_filtered['API_WELL_NUMBER'] == api][['WAR_START_DT', 'WAR_END_DT']].dropna()
            war_dates = war_dates[war_dates['WAR_START_DT'] <= td]
            if war_dates.empty or pd.isna(td):
                return td, 0

            war_dates = war_dates.sort_values(by='WAR_START_DT').reset_index(drop=True)
            war_dates['GAP'] = war_dates['WAR_START_DT'].diff().dt.days

            if (td - war_dates.loc[0, 'WAR_START_DT']).days <= GAP_THRESHOLD:
                return war_dates.loc[0, 'WAR_START_DT'], 0

            gap_idx = war_dates.index[war_dates['GAP'] > GAP_THRESHOLD].tolist()
            if gap_idx:
                last_gap_idx = gap_idx[-1]
                if last_gap_idx + 1 < len(war_dates):
                    spud_after_gap = war_dates.loc[last_gap_idx + 1, 'WAR_START_DT']
                    early_days = (war_dates.loc[:last_gap_idx, 'WAR_END_DT'] - war_dates.loc[:last_gap_idx, 'WAR_START_DT']).dt.days.sum()
                    return spud_after_gap, int(early_days)

            return war_dates.loc[0, 'WAR_START_DT'], 0

        rows = []
        for _, row in td_from_boreholes.iterrows():
            api = row['API_WELL_NUMBER']
            td = row['TOTAL_DEPTH_DATE']
            spud, early_days = adjust_spud(api, td)
            if pd.notna(spud) and pd.notna(td) and td > spud:
                rows.append((api, spud, td, (td - spud).days - early_days))

        spud_td = pd.DataFrame(rows, columns=['API_WELL_NUMBER', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE', 'DRILLING_DAYS'])
        
        # Completion estimation from WAR timeline after TD
        COMPLETION_GAP_THRESHOLD = 8
        
        completion_segments = []
        for _, row in spud_td.iterrows():
            api = row['API_WELL_NUMBER']
            td = row['TOTAL_DEPTH_DATE']
            completions = self.main_war_filtered[
                (self.main_war_filtered['API_WELL_NUMBER'] == api) &
                (self.main_war_filtered['WAR_START_DT'] > td)
            ][['WAR_START_DT', 'WAR_END_DT']].dropna().sort_values(by='WAR_START_DT')

            if completions.empty:
                completion_segments.append((api, 0))
                continue

            completions = completions.reset_index(drop=True)
            completions['GAP'] = completions['WAR_START_DT'].diff().dt.days.fillna(0)

            segment_days = 0
            start_idx = 0
            for i in range(1, len(completions)):
                if completions.loc[i, 'GAP'] > COMPLETION_GAP_THRESHOLD:
                    segment = completions.loc[start_idx:i-1]
                    segment_days += (segment['WAR_END_DT'] - segment['WAR_START_DT']).dt.days.sum()
                    start_idx = i
            # Add final segment
            segment = completions.loc[start_idx:]
            segment_days += (segment['WAR_END_DT'] - segment['WAR_START_DT']).dt.days.sum()

            completion_segments.append((api, max(segment_days, 0)))

        completion_summary = pd.DataFrame(completion_segments, columns=['API_WELL_NUMBER', 'COMPLETION_DAYS'])
        final = spud_td.merge(completion_summary, on='API_WELL_NUMBER', how='left')
        final['COMPLETION_DAYS'] = final['COMPLETION_DAYS'].fillna(0).astype(int)
        
        # Add WELL_NAME, LEASE info
        final['WELL_NAME'] = final['API_WELL_NUMBER'].map(
            self.main_war_filtered.dropna(subset=['WELL_NAME']).drop_duplicates('API_WELL_NUMBER').set_index('API_WELL_NUMBER')['WELL_NAME']
        )
        api_to_lease = (
            self.main_war_filtered.drop_duplicates('API_WELL_NUMBER')
            .assign(SURF_LEASE_NUM=lambda df: df['SURF_LEASE_NUM'].str.upper().str.replace('^G', '', regex=True).str.strip())
            .set_index('API_WELL_NUMBER')['SURF_LEASE_NUM']
            .to_dict()
        )
        final['SURF_LEASE_NUM'] = final['API_WELL_NUMBER'].map(api_to_lease)
        
        # Debug: log mapping sample
        logger.info("Sample API to Lease Mapping:")
        for api in list(final['API_WELL_NUMBER'].unique())[:5]:
            lease_num = api_to_lease.get(api, 'N/A')
            lease_meta = self.lease_info.get(lease_num, {})
            logger.info(f"API: {api} → Lease#: {lease_num} → Name: {lease_meta.get('LEASE_NAME', '')}, Depth: {lease_meta.get('WATER_DEPTH', '')}")

        final['LEASE_NAME'] = final['SURF_LEASE_NUM'].map(lambda x: self.lease_info.get(x, {}).get('LEASE_NAME', ''))
        final['WATER_DEPTH'] = final['SURF_LEASE_NUM'].map(lambda x: self.lease_info.get(x, {}).get('WATER_DEPTH', ''))
        
        # Merge depths and mud
        final = final.merge(depth_summary, on='API_WELL_NUMBER', how='left')
        final = final.merge(mud_summary, on='API_WELL_NUMBER', how='left')
        
        # Format and export
        final['WELL_SPUD_DATE'] = pd.to_datetime(final['WELL_SPUD_DATE']).dt.strftime('%m/%d/%Y')
        final['TOTAL_DEPTH_DATE'] = pd.to_datetime(final['TOTAL_DEPTH_DATE']).dt.strftime('%m/%d/%Y')
        final = final[['LEASE_NAME', 'SURF_LEASE_NUM', 'WATER_DEPTH', 'API_WELL_NUMBER', 'WELL_NAME', 'WELL_SPUD_DATE',
                       'TOTAL_DEPTH_DATE', 'DRILLING_DAYS', 'COMPLETION_DAYS',
                       'MAX_BH_TOTAL_MD', 'MAX_WELL_BORE_TVD', 'MAX_DRILL_FLUID_WGT']]
        final = final.dropna(subset=['WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE'])
        final['SPUD_DATE_SORT'] = pd.to_datetime(final['WELL_SPUD_DATE'], errors='coerce')
        final = final.sort_values(by=['LEASE_NAME', 'SPUD_DATE_SORT']).drop(columns=['SPUD_DATE_SORT'])
        
        # Generate output filename based on configuration or default
        output_filename = "drilling_and_completion_days_by_api_latest.xlsx"
        result_path = self.cfg['Analysis']['result_folder']
        final.to_excel(os.path.join(result_path, output_filename), index=False)
        logger.info(f"Analysis results written to: {output_filename}")
        logger.info(f"Processed {len(final)} wells with drilling and completion data")