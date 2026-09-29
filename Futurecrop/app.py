# app.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime
from pathlib import Path
import csv
import random
import statistics


# =========================================================
# CONFIGURATION
# =========================================================

HOST = "0.0.0.0"
PORT = 5000

BASE_DIR = Path(__file__).resolve().parent
MOCK_CSV = BASE_DIR / "mock_prices.csv"


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="FutureCrop - AI Price Prediction API",
    version="1.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


# =========================================================
# REQUEST MODEL
# =========================================================

class PredictRequest(BaseModel):

    state: str = Field(
        ...,
        example="Andhra Pradesh"
    )

    district: Optional[str] = Field(
        None,
        example="Ananthapuramu"
    )

    market: Optional[str] = Field(
        None,
        example="Main Market"
    )

    crop: str = Field(
        ...,
        example="Tomato"
    )

    month: str = Field(
        ...,
        example="2027-11"
    )


# =========================================================
# RESPONSE MODEL
# =========================================================

class PredictResponse(BaseModel):

    state: str
    district: Optional[str]
    market: Optional[str]
    crop: str
    month: str
    unit: str

    currentPrice: float
    predictedPrice: float

    method: str


# =========================================================
# CROP BASE PRICES
# ₹ PER KG
# =========================================================

BASE_PRICES = {

    "turnip": 25,
    "ash gourd": 20,
    "snake gourd": 30,
    "ridge gourd": 30,
    "ivy gourd": 35,
    "squash": 25,

    "cluster beans": 40,
    "broad beans": 35,
    "peas": 35,
    "field beans": 32,

    "lady's finger": 30,
    "jute": 45,
    "bengal gram": 70,
    "barley": 35,
    "jowar": 32,
    "black gram": 80,

    "tomato": 32,
    "onion": 28,
    "potato": 24,

    "rice": 35,
    "wheat": 30,
    "paddy": 34,
    "corn": 22,
    "bajra": 26,

    "cotton": 65,
    "sugarcane": 36,

    "mango": 50,
    "banana": 30,
    "pomegranate": 70,
    "papaya": 28,

    "brinjal": 30,
    "cabbage": 22,
    "cauliflower": 25,
    "carrot": 28,
    "spinach": 18,
    "beetroot": 26,
    "sweet potato": 27,
    "cucumber": 23,
    "radish": 20,
    "pumpkin": 18,
    "drumstick": 45,
    "jackfruit": 35,
    "green beans": 40,
    "capsicum": 45,
    "bottle gourd": 20,
    "elephant foot yam": 32
}


# =========================================================
# LOAD CSV
# =========================================================

def load_mock_data():

    data = []

    if not MOCK_CSV.exists():

        print("mock_prices.csv not found.")

        return data


    try:

        with open(
            MOCK_CSV,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                try:
                    price = float(
                        row.get("price") or 0
                    )
                except:
                    price = 0.0


                data.append({

                    "state":
                        row.get("state", "").strip(),

                    "district":
                        row.get("district", "").strip(),

                    "market":
                        row.get("market", "").strip(),

                    "crop":
                        row.get("crop", "").strip(),

                    "date":
                        row.get("date", "").strip(),

                    "price":
                        price,

                    "unit":
                        row.get(
                            "unit",
                            "kg"
                        ).strip().lower()

                })


    except Exception as error:

        print(
            "Error loading CSV:",
            error
        )


    print(
        f"Loaded {len(data)} price records."
    )

    return data


MOCK_DATA = load_mock_data()


# =========================================================
# MONTH VALIDATION
# =========================================================

def month_to_date(month):

    try:

        return datetime.strptime(
            month + "-01",
            "%Y-%m-%d"
        )

    except:

        raise ValueError(
            "Month must be in YYYY-MM format"
        )


# =========================================================
# FIND RECENT PRICE
# =========================================================

def find_recent_price(
    state,
    district,
    crop,
    market
):

    if not MOCK_DATA:

        return None


    # First try exact crop + state + district
    candidates = []


    for row in MOCK_DATA:

        if row["crop"].lower() != crop.lower():
            continue


        if state:

            if row["state"].lower() != state.lower():
                continue


        if district:

            if row["district"]:

                if (
                    row["district"].lower()
                    != district.lower()
                ):
                    continue


        if market:

            if row["market"]:

                if (
                    row["market"].lower()
                    != market.lower()
                ):
                    continue


        candidates.append(row)


    # If no exact result,
    # search crop + state
    if not candidates:

        candidates = [

            row for row in MOCK_DATA

            if (
                row["crop"].lower()
                == crop.lower()
                and
                row["state"].lower()
                == state.lower()
            )

        ]


    # If still no result,
    # search only crop
    if not candidates:

        candidates = [

            row for row in MOCK_DATA

            if row["crop"].lower()
            == crop.lower()

        ]


    if not candidates:

        return None


    # Find latest dated record

    dated_records = []


    for row in candidates:

        try:

            date = datetime.strptime(
                row["date"],
                "%Y-%m-%d"
            )

            dated_records.append(
                (date, row)
            )

        except:

            pass


    if dated_records:

        dated_records.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return dated_records[0][1]


    # Otherwise median price

    prices = [

        row["price"]

        for row in candidates

        if row["price"] > 0

    ]


    if prices:

        median_price = statistics.median(
            prices
        )

        result = candidates[0].copy()

        result["price"] = median_price

        return result


    return None


# =========================================================
# CONVERT PRICE TO ₹/QUINTAL
# =========================================================

def convert_to_quintal(
    price,
    unit
):

    unit = unit.lower().strip()


    # 1 Quintal = 100 KG

    if unit in [
        "kg",
        "₹/kg",
        "rs/kg",
        "inr/kg"
    ]:

        return price * 100


    if unit in [
        "quintal",
        "quintals",
        "qtl",
        "₹/quintal",
        "rs/quintal"
    ]:

        return price


    # Default assumption:
    # price is per kg

    return price * 100


# =========================================================
# SIMPLE PREDICTION
# =========================================================

def simple_predict(
    current_price,
    months_ahead,
    crop
):

    crop_name = crop.lower()


    # Volatility

    high_volatility = {

        "tomato",
        "onion",
        "pomegranate",
        "mango"

    }


    medium_volatility = {

        "potato",
        "capsicum",
        "brinjal",
        "banana",
        "peas"

    }


    if crop_name in high_volatility:

        volatility = 0.08

    elif crop_name in medium_volatility:

        volatility = 0.05

    else:

        volatility = 0.03


    price = current_price


    # Prediction for future months

    for _ in range(months_ahead):

        change = random.gauss(
            0,
            volatility
        )

        price = price * (
            1 + change
        )


    # Small upward trend

    price = price * (
        1 + (0.005 * months_ahead)
    )


    return round(
        max(price, 1),
        2
    )


# =========================================================
# PREDICT API
# =========================================================

@app.post(
    "/predict",
    response_model=PredictResponse
)
async def predict(
    req: PredictRequest
):

    # ---------------------------------------------
    # Validate month
    # ---------------------------------------------

    try:

        target_date = month_to_date(
            req.month
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    # ---------------------------------------------
    # Calculate months ahead
    # ---------------------------------------------

    now = datetime.now()


    months_ahead = (

        (target_date.year - now.year)
        * 12

        +

        (target_date.month - now.month)

    )


    if months_ahead < 0:

        months_ahead = 0


    # ---------------------------------------------
    # Search CSV
    # ---------------------------------------------

    record = find_recent_price(

        req.state,

        req.district or "",

        req.crop,

        req.market or ""

    )


    # ---------------------------------------------
    # Current price
    # ---------------------------------------------

    if record and record["price"] > 0:

        raw_price = float(
            record["price"]
        )

        original_unit = (
            record.get("unit", "kg")
            or "kg"
        )


        # Convert ₹/kg → ₹/Quintal

        current_price = convert_to_quintal(

            raw_price,

            original_unit

        )


        method = "mock-data"


    else:

        # -----------------------------------------
        # Fallback price
        # -----------------------------------------

        raw_price = BASE_PRICES.get(

            req.crop.lower(),

            25

        )


        # Base prices are ₹/kg

        current_price = (
            raw_price * 100
        )


        method = "synthetic"


    # ---------------------------------------------
    # Prediction
    # ---------------------------------------------

    predicted_price = simple_predict(

        current_price,

        months_ahead,

        req.crop

    )


    # ---------------------------------------------
    # Response
    # ---------------------------------------------

    return PredictResponse(

        state=req.state,

        district=req.district,

        market=req.market,

        crop=req.crop,

        month=req.month,

        unit="₹/Quintal",

        currentPrice=round(
            current_price,
            2
        ),

        predictedPrice=round(
            predicted_price,
            2
        ),

        method=method

    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


# =========================================================
# GET /predict
# =========================================================

@app.get("/predict")
def predict_info():

    return {

        "message":
            "FutureCrop Prediction API",

        "method":
            "Use POST for predictions",

        "endpoint":
            "/predict"

    }


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "app:app",

        host=HOST,

        port=PORT,

        reload=True

    )