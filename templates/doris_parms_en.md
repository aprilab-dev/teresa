# Teresa Configuration Parameters Description

This document provides a detailed explanation of the configuration file parameters in `Teresa`, helping users better understand and adjust the processing workflow.

---

## 📁 stack_parameters – Stack Parameters

| Parameter   | Description |
|-------------|-------------|
| work_dir    | Path to the working directory |
| data_dirs   | Path(s) to the input SLC data (can be single or multiple paths) |
| masterDate  | Master image date (format: YYYYMMDD). If left empty, the optimal master image will be automatically selected |

---

## 🛰 coarsecorr – Coarse Coregistration Parameters

| Parameter   | Description | Value |
|-------------|-------------|-------|
| CC_METHOD   | Method used for correlation calculation on amplitude images | `magfft`: FFT in frequency domain; `magspace`: direct computation in spatial domain |
| CC_ACC      | Search range for master-slave offset. For `magfft`, it defaults to half the window size; for `magspace`, must be manually set | Format: `<lines> <pixels>`, e.g., `9 9` means search ±8 pixels |
| CC_NWIN     | Number of windows used for offset correlation estimation | ≥ 5 recommended; more windows = stable, fewer = higher bias |
| CC_WINSIZE  | Window size for correlation calculation | Format: `<lines> <pixels>` |
| CC_INITOFF  | Initial offset for coarse coregistration | Format: `orbit` (use result from coarseorb step) or two numbers (manual offset) |

---

## 🔍 fine – Fine Coregistration Parameters

| Parameter   | Description | Value |
|-------------|-------------|-------|
| FC_METHOD   | Fine coregistration method | `magfft`: frequency domain (fast, padding changes patch size); `magspace`: spatial domain (stable patch size, slower); `oversample`: frequency domain + oversampling (best accuracy) |
| FC_NWIN     | Number of correlation windows distributed over the image | More windows = better stability |
| FC_WINSIZE  | Correlation window size (rows × columns) | Larger = stable but may smooth details; smaller = sensitive to noise |
| FC_ACC      | Accuracy (in pixels, format: "azimuth range") | Suggested `8 8`. For FFT methods, must be power of 2 (4, 8, 16, 32). If coarse and fine offsets differ by >1, increase window size and accuracy |
| FC_INITOFF  | Initial offset setting | `coarsecorr`: use result from coarsecorr step |
| FC_OSFACTOR | Oversampling factor | Recommended 32 → improves precision to <0.1 pixels |
| FC_SHIFTAZI | Correct azimuth shift | `ON` / `OFF` |

---

## 🔄 coregpm – Polynomial Modeling for Fine Coregistration

| Parameter    | Description | Value |
|--------------|-------------|-------|
| CPM_THRESHOLD| Correlation threshold for polynomial coefficient estimation | Depends on window size. Smaller windows → higher correlations → set a higher threshold. For 64×64 window, threshold `0.2` is good |
| CPM_DEGREE   | Degree of the 2D polynomial | Suggested: 2 |
| CPM_WEIGHT   | Weighting strategy for least-squares fitting based on correlation | `BAMLER`: default, most robust; `NONE`: equal weights; `LINEAR`: correlation value; `QUADRATIC`: correlation² |
| CPM_MAXITER  | Maximum iterations | DORIS repeats fitting, removing outliers each iteration until stable or reaching limit |

---

## 🎯 resample – Resampling Parameters

| Parameter   | Description | Value |
|-------------|-------------|-------|
| RS_METHOD   | Interpolation kernel | `RECT`: nearest neighbor; `TRI`: linear; `CC4P/CC6P`: cubic convolution; `TS6P/TS8P/TS16P`: truncated sinc; `KNAB6/8/10/16`: Knab window; `RC6P/RC12P`: Raised Cosine (recommended) |
| RS_SHIFTAZI | Correct azimuth shift | `ON`: align spectrum to Doppler center (recommended when Doppler is large); `OFF`: no alignment (use if Doppler ~0) |
| RS_OUT_FILE | Output resampled file name (e.g., `slave_rsmp.raw`) |
| RS_OUT_FORMAT| Output data format | `CR4`: complex float32; `CI2`: complex int16 (typical SLC format) |

---

## 🌗 interfero – Interferogram Generation Parameters

| Parameter     | Description | Value |
|---------------|-------------|-------|
| INT_OUT_CINT  | Output complex interferogram file | e.g., `interfero.raw` |
| INT_MULTILOOK | Multilook factors ("azimuth range") | If no multilook required, set to `1 1` |

---

## 🗺 dem – Digital Elevation Model Parameters

| Parameter       | Description | Value |
|-----------------|-------------|-------|
| CRD_IN_DEM      | Input DEM file path |
| CRD_IN_FORMAT   | DEM format | `r4`: float32 (e.g., SRTM); `r8`: float64 |
| CRD_IN_SIZE     | DEM size ("rows columns") |
| CRD_IN_DELTA    | DEM resolution ("lat_step lon_step") | e.g., SRTM = `0.000277777777778 0.000277777777778` |
| CRD_IN_UL       | DEM upper-left corner ("lat lon") | Latitude -90~+90, Longitude -180~+180 |
| CRD_IN_NODATA   | No-data marker value | Points with this value ignored |
| CRD_OUT_FILE    | DEM output file (use `/dev/null` to skip) |
| CRD_OUT_DEM_LP  | Output DEM in radar coordinates |

---

✳️ More module parameters will be added in future versions.  
✳️ See also the DORIS technical manual.  
