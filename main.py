from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import io
from typing import List, Dict
from pydantic import BaseModel

app = FastAPI()

# Configure CORS - adjust for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define required columns and their expected data types
REQUIRED_COLUMNS = {
    "road_name": str,
    "pcivalue_2019": int,
    "pcivalue_2021": int
}

# Pydantic model for response validation
class RoadData(BaseModel):
    road_name: str
    pcivalue_2019: int
    pcivalue_2021: int

class ErrorResponse(BaseModel):
    detail: str

@app.post("/upload_excel/", 
          response_model=List[RoadData],
          responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_excel(file: UploadFile = File(...)):
    """
    Endpoint for uploading Excel files containing road PCI data.
    
    Expected Excel format:
    - Must contain columns: road_name, pcivalue_2019, pcivalue_2021
    - PCI values must be integers between 1-5
    - First row should be headers
    
    Returns parsed data as JSON if valid.
    """
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Try to parse as Excel
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Excel file. Please upload a valid .xlsx file. Error: {str(e)}"
            )
        
        # Check for required columns (case insensitive)
        df.columns = df.columns.str.lower()  # Normalize column names to lowercase
        missing_columns = [col for col in REQUIRED_COLUMNS.keys() if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}. "
                       f"Required columns are: {', '.join(REQUIRED_COLUMNS.keys())}"
            )
        
        # Filter to only required columns
        df = df[list(REQUIRED_COLUMNS.keys())].copy()
        
        # Clean data
        df = df.dropna()  # Remove rows with any missing values
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # Strip whitespace from strings
        
        # Validate data types
        validation_errors = []
        
        for index, row in df.iterrows():
            # Check PCI values are integers between 1-5
            try:
                pci_2019 = int(row['pcivalue_2019'])
                pci_2021 = int(row['pcivalue_2021'])
                
                if not (1 <= pci_2019 <= 5):
                    validation_errors.append(
                        f"Row {index + 2}: pcivalue_2019 must be between 1-5, got {pci_2019}"
                    )
                if not (1 <= pci_2021 <= 5):
                    validation_errors.append(
                        f"Row {index + 2}: pcivalue_2021 must be between 1-5, got {pci_2021}"
                    )
                    
            except ValueError:
                validation_errors.append(
                    f"Row {index + 2}: PCI values must be integers"
                )
            
            # Check road name is not empty
            if not str(row['road_name']).strip():
                validation_errors.append(
                    f"Row {index + 2}: road_name cannot be empty"
                )
        
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail="Data validation errors:\n" + "\n".join(validation_errors)
            )
        
        # Convert to list of dictionaries
        result = df.to_dict(orient='records')
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions we created
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# For testing locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
