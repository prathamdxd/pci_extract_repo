from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
import io

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>PCI Analysis API</title>
        </head>
        <body>
            <h1>PCI Analysis API</h1>
            <p>Use POST /upload_excel/ to upload Excel files</p>
        </body>
    </html>
    """

# Excel upload endpoint
@app.post("/upload_excel/")
async def upload_excel(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(400, "Only Excel files are allowed")

        # Read and parse file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        
        # Validate columns
        required = ["road_name", "pcivalue_2019", "pcivalue_2021"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise HTTPException(400, f"Missing columns: {', '.join(missing)}")

        # Convert to list of dictionaries
        data = df[required].to_dict(orient='records')
        return {"status": "success", "data": data}
        
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
