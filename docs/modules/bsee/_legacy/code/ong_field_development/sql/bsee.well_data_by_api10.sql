DECLARE @API_WELL_NUMBER NVARCHAR(10) = {};

--DECLARE @API_WELL_NUMBER NVARCHAR(10) = '6081240095';

SELECT API12, API10, [Company Name], [Field Name], [Well Name], [Sidetrack and Bypass]
, [Spud Date], [Total Depth Date], [Well Purpose]
, [Water Depth], [Total Measured Depth], [Total Vertical Depth], [Sidetrack KOP]
, [Surface Latitude], [Surface Longitude], [Bottom Latitude], [Bottom Longitude]
, [Wellbore Status], [Wellbore Status Date], [Completion Stub Code], [Casing Cut Code]
FROM

(SELECT [API_WELL_NUMBER] as API12, LEFT(API_WELL_NUMBER,10) as API10, BOTM_FLD_NAME_CD as [Field Name], COMPANY_NAME as [Company Name]
, WELL_NAME as [Well Name], WELL_NAME_SUFFIX as [Sidetrack and Bypass], WELL_SPUD_DATE as [Spud Date]
, TOTAL_DEPTH_DATE as [Total Depth Date], BH_TOTAL_MD as [BH Total MD (feet)]
FROM [dbo].[mv_api_list]
WHERE LEFT(API_WELL_NUMBER,10) = @API_WELL_NUMBER
)
AS APIListTable

JOIN
(SELECT SURF_LATITUDE as [Surface Latitude], SURF_LONGITUDE as [Surface Longitude], BOTM_LATITUDE as [Bottom Latitude], BOTM_LONGITUDE as [Bottom Longitude], API_WELL_NUMBER as WELLAPI
, [WELL_TYPE_CODE] as [Well Purpose], BOREHOLE_STAT_CD as [Wellbore Status], BOREHOLE_STAT_DT as [Wellbore Status Date]
, WATER_DEPTH as [Water Depth]
, TOTAL_DEPTH_DATE as [Total Measured Depth], WELL_BORE_TVD as [Total Vertical Depth]
, WELL_BP_ST_KICKOFF_MD as [Sidetrack KOP]
, UNDWTR_COMP_STUB as [Completion Stub Code], CASING_CUT_CODE as [Casing Cut Code]
FROM [dbo].[mv_boreholes]
)
AS borehole
on APIListTable.API12 = borehole.WELLAPI