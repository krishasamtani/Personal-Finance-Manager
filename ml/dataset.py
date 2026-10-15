"""Synthetic bank-statement descriptions used to bootstrap the categoriser.

Real statements are noisy ("UPI/SWIGGY/48213@okhdfcbank"), so each merchant is wrapped in
random statement-style templates. The model is later personalised with the user's own labels.
"""
import numpy as np
import pandas as pd

MERCHANTS = {
    "Food": ["Swiggy", "Zomato", "Dominos", "McDonalds", "KFC", "Starbucks", "Cafe Coffee Day", "Haldirams",
             "Burger King", "Pizza Hut", "Chaayos", "Barbeque Nation", "Behrouz Biryani", "Subway", "Faasos"],
    "Groceries": ["BigBasket", "Blinkit", "Zepto", "DMart", "Reliance Fresh", "Swiggy Instamart", "More Supermarket",
                  "Natures Basket", "Milk Basket", "Local Kirana Store", "Vegetable Vendor"],
    "Rent": ["House Rent", "Rent Payment", "PG Rent", "Hostel Rent", "Landlord", "Monthly Rent", "NoBroker Rent",
             "Society Maintenance", "Flat Rent"],
    "Utilities": ["Jio Recharge", "Airtel Postpaid", "Vi Recharge", "BSNL Broadband", "Electricity Bill MSEDCL",
                  "Tata Power", "Adani Electricity", "Mahanagar Gas", "Water Bill", "ACT Fibernet", "Tata Play",
                  "Indane Gas Cylinder", "BESCOM"],
    "Entertainment": ["Netflix", "Amazon Prime", "Hotstar", "Spotify", "BookMyShow", "PVR Cinemas", "INOX",
                      "YouTube Premium", "Steam Games", "Sony Liv", "Zee5", "Gaming Zone"],
    "Investment": ["Zerodha", "Groww SIP", "Mutual Fund SIP", "Upstox", "NPS Contribution", "PPF Deposit",
                   "SBI Mutual Fund", "HDFC Mutual Fund", "Kuvera", "Gold Bond", "Recurring Deposit", "Fixed Deposit"],
    "Transport": ["Uber", "Ola", "Rapido", "Metro Recharge", "Indian Oil Petrol", "HP Petrol Pump",
                  "Bharat Petroleum", "FASTag Recharge", "Parking Fee", "Mumbai Local Pass", "BEST Bus",
                  "Auto Rickshaw"],
    "Shopping": ["Amazon", "Flipkart", "Myntra", "Ajio", "Nykaa", "Decathlon", "Croma", "Reliance Digital", "Zara",
                 "Lifestyle", "Westside", "Meesho", "Ikea"],
    "Health": ["Apollo Pharmacy", "Tata 1mg", "PharmEasy", "Practo", "Medplus", "Netmeds", "Cult Fit",
               "Dr Lal PathLabs", "Hospital Bill", "Dental Clinic", "Gym Membership", "Diagnostic Center"],
    "Education": ["Udemy", "Coursera", "College Fees", "Exam Fee", "Unacademy", "Byjus", "Stationery Store",
                  "Crossword Book Store", "NPTEL Exam Fee", "LeetCode Premium", "Library Fee", "Tuition Fee"],
    "Travel": ["IRCTC", "MakeMyTrip", "Goibibo", "IndiGo", "Air India", "OYO Rooms", "Booking.com", "Airbnb",
               "RedBus", "Yatra", "Cleartrip", "Hotel Stay"],
    "Other": ["ATM Withdrawal", "Cash Withdrawal", "Bank Charges", "Misc Payment", "Donation", "Gift Purchase",
              "UPI Transfer To Friend", "Late Fee", "Insurance Premium", "Unknown Merchant", "Service Charge GST"],
    "Salary": ["Salary Credit", "Infosys Salary", "TCS Payroll", "Monthly Salary", "Internship Stipend",
               "Wipro Salary", "Company Payroll", "Accenture Salary", "NEFT Salary"],
    "Freelance": ["Freelance Payment", "Upwork Withdrawal", "Fiverr Payout", "Client Payment", "Project Payment",
                  "Consulting Fee", "Paypal Client Transfer"],
    "Interest": ["Savings Interest", "FD Interest", "Interest Credit", "Dividend Credit", "Bank Interest",
                 "Dividend Reliance"],
    "Refund": ["Amazon Refund", "Swiggy Refund", "Cashback Credit", "Payment Reversal", "Flipkart Refund",
               "Paytm Cashback", "Order Refund"],
}

# Generic words people actually see/type; lets the model generalise beyond memorised merchant names.
_GENERIC = {
    "Food": ["Restaurant Bill", "Dinner at Cafe", "Lunch Canteen", "Bakery", "Food Court", "Biryani House",
             "Tea Stall", "Juice Center", "Ice Cream Parlour", "Dhaba"],
    "Groceries": ["Supermarket", "Grocery Store", "Fruits And Vegetables", "Provision Store", "Kirana",
                  "Dairy Milk", "Bread Eggs Groceries"],
    "Rent": ["Rent For Month", "Room Rent", "Apartment Rent", "Rent Transfer"],
    "Utilities": ["Electricity Bill", "Mobile Recharge", "Broadband Bill", "Gas Bill", "Postpaid Bill Payment",
                  "DTH Recharge", "Water Charges", "Internet Bill"],
    "Entertainment": ["Movie Tickets", "Streaming Subscription", "Music Subscription", "Concert Tickets",
                      "Video Game", "OTT Subscription", "Multiplex"],
    "Investment": ["Mutual Fund Purchase", "SIP Instalment", "Stock Purchase", "Demat Account Credit",
                   "Bond Purchase", "Systematic Investment Plan", "Equity Trade"],
    "Transport": ["Cab Ride", "Petrol Pump", "Fuel Station", "Bus Ticket", "Toll Plaza", "Metro Card Recharge",
                  "Auto Fare", "Taxi Fare"],
    "Shopping": ["Online Shopping", "Clothing Store", "Electronics Store", "Shoe Store", "Fashion Outlet",
                 "Mall Purchase", "Gadget Store"],
    "Health": ["Pharmacy", "Medical Store", "Doctor Consultation", "Clinic Fees", "Pathology Lab",
               "Hospital Charges", "Health Checkup", "Medicines"],
    "Education": ["Course Fee", "Online Course", "Tuition Classes", "Books Purchase", "Coaching Fees",
                  "University Fees", "Workshop Registration"],
    "Travel": ["Flight Ticket", "Hotel Booking", "Train Ticket", "Holiday Package", "Resort Stay",
               "Travel Booking", "Airline Booking"],
    "Other": ["Miscellaneous", "Cash Deposit Charges", "Annual Fee", "Penalty Charges", "Transfer To Self",
              "Unknown Payment"],
    "Salary": ["Salary For Month", "Monthly Pay", "Stipend Credit", "Wages Credit", "Payroll Credit"],
    "Freelance": ["Freelance Income", "Gig Payment", "Contract Payment", "Invoice Payment", "Consulting Income"],
    "Interest": ["Interest Paid", "Dividend Received", "Interest On Savings", "Quarterly Interest"],
    "Refund": ["Refund Processed", "Money Back", "Cashback Received", "Order Cancelled Refund", "Refund Credit"],
}
for _cat, _words in _GENERIC.items():
    MERCHANTS[_cat] = MERCHANTS[_cat] + _words

_TEMPLATES = ["{m}", "{m}", "UPI/{m}/{ref}@{bank}", "POS {ref} {m}", "{m} PAYMENT", "NEFT-{m}-{ref}",
              "{m} {city}", "PAYTM {m}", "IMPS/{ref}/{m}", "{m} ORDER {ref}", "{m} TXN {ref}"]
_CITIES = ["MUMBAI", "PUNE", "BANGALORE", "DELHI", "HYDERABAD", "CHENNAI", "NAGPUR"]
_BANKS = ["okhdfcbank", "oksbi", "okaxis", "ybl", "ibl", "paytm"]


def noisy(merchant, rng):
    """Wrap a merchant name in a random bank-statement style template."""
    s = str(rng.choice(_TEMPLATES)).format(
        m=merchant, ref=int(rng.integers(10_000, 999_999_999)), bank=str(rng.choice(_BANKS)),
        city=str(rng.choice(_CITIES)))
    r = rng.random()
    return s.upper() if r < 0.3 else s.lower() if r < 0.5 else s


def generate_dataset(n_per_class=120, seed=42):
    """DataFrame[description, category, merchant]; `merchant` is used for grouped evaluation."""
    rng = np.random.default_rng(seed)
    rows = []
    for category, merchants in MERCHANTS.items():
        for _ in range(n_per_class):
            m = merchants[int(rng.integers(len(merchants)))]
            rows.append({"description": noisy(m, rng), "category": category, "merchant": m})
    return pd.DataFrame(rows)
