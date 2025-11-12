import random
from decimal import Decimal
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import Account, Holding

# Realistic asset data
ASSET_DATA = {
    "Stock": [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "price_range": (150, 200), "dividend": 0.5},
        {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology", "price_range": (300, 400), "dividend": 0.8},
        {"symbol": "GOOGL", "name": "Alphabet", "sector": "Technology", "price_range": (130, 150), "dividend": 0.0},
        {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "price_range": (150, 170), "dividend": 2.5},
        {"symbol": "JPM", "name": "JPMorgan Chase", "sector": "Financial", "price_range": (140, 180), "dividend": 2.8},
        {"symbol": "XOM", "name": "Exxon Mobil", "sector": "Energy", "price_range": (100, 120), "dividend": 3.5},
        {"symbol": "WMT", "name": "Walmart", "sector": "Consumer", "price_range": (150, 170), "dividend": 1.5},
    ],
    "ETF": [
        {"symbol": "VTI", "name": "Vanguard Total Market", "sector": "Total Market", "price_range": (220, 260), "dividend": 1.3},
        {"symbol": "VOO", "name": "Vanguard S&P 500", "sector": "Large Cap", "price_range": (400, 450), "dividend": 1.4},
        {"symbol": "VEA", "name": "Vanguard Developed Markets", "sector": "International", "price_range": (45, 52), "dividend": 2.8},
        {"symbol": "VWO", "name": "Vanguard Emerging Markets", "sector": "Emerging", "price_range": (40, 48), "dividend": 3.2},
        {"symbol": "AGG", "name": "iShares Core US Aggregate", "sector": "Bonds", "price_range": (95, 105), "dividend": 3.5},
    ],
    "Bond": [
        {"symbol": "BND", "name": "Vanguard Total Bond", "sector": "Fixed Income", "price_range": (70, 78), "dividend": 3.8},
        {"symbol": "TLT", "name": "iShares 20+ Year Treasury", "sector": "Treasury", "price_range": (90, 110), "dividend": 4.0},
        {"symbol": "MUB", "name": "iShares National Muni", "sector": "Municipal", "price_range": (105, 115), "dividend": 2.5},
    ],
    "Cash": [
        {"symbol": "CASH", "name": "Cash & Equivalents", "sector": "Money Market", "price_range": (1, 1), "dividend": 4.5},
    ]
}

ACCOUNT_TYPES = [
    {"name": "Traditional IRA", "type": "retirement", "allocation": {"Stock": 0.5, "ETF": 0.3, "Bond": 0.15, "Cash": 0.05}},
    {"name": "Roth IRA", "type": "retirement", "allocation": {"Stock": 0.6, "ETF": 0.25, "Bond": 0.1, "Cash": 0.05}},
    {"name": "401(k)", "type": "retirement", "allocation": {"ETF": 0.65, "Bond": 0.25, "Cash": 0.1}},
    {"name": "Brokerage Account", "type": "taxable", "allocation": {"Stock": 0.55, "ETF": 0.25, "Bond": 0.1, "Cash": 0.1}},
    {"name": "Individual Brokerage", "type": "taxable", "allocation": {"Stock": 0.6, "ETF": 0.2, "Bond": 0.15, "Cash": 0.05}},
    {"name": "High-Yield Savings", "type": "cash", "allocation": {"Cash": 1.0}},
    {"name": "Money Market", "type": "cash", "allocation": {"Cash": 1.0}},
]

INSTITUTIONS = ["J.P. Morgan", "Fidelity", "Vanguard", "Charles Schwab", "Morgan Stanley", "Merrill Lynch"]


def generate_portfolio_data(user_id: str, db: Session, risk_tolerance: str = "medium"):
    """Generate realistic portfolio data for a new user"""
    
    # Determine account count based on risk profile
    num_accounts = random.randint(5, 8)
    
    # Select account types (ensure diversity)
    selected_accounts = random.sample(ACCOUNT_TYPES, min(num_accounts, len(ACCOUNT_TYPES)))
    
    accounts_created = []
    
    for acct_template in selected_accounts:
        # Generate account balance (higher for retirement accounts)
        if acct_template["type"] == "retirement":
            balance = Decimal(random.randint(15000, 85000))
        elif acct_template["type"] == "taxable":
            balance = Decimal(random.randint(10000, 60000))
        else:  # cash
            balance = Decimal(random.randint(5000, 30000))
        
        # Create account
        account = Account(
            user_id=user_id,
            name=acct_template["name"],
            account_type=acct_template["type"],
            institution=random.choice(INSTITUTIONS),
            last4=str(random.randint(1000, 9999)),
            balance=balance,
            ytd_return=Decimal(random.uniform(-2, 15))  # Realistic annual return
        )
        db.add(account)
        db.flush()  # Get account ID
        
        # Generate holdings based on allocation
        num_holdings = random.randint(3, 9)
        allocation = acct_template["allocation"]
        
        # Distribute balance across asset classes
        remaining_balance = float(balance)
        holdings_created = []
        
        for asset_class, target_pct in allocation.items():
            if asset_class not in ASSET_DATA:
                continue
                
            assets_in_class = ASSET_DATA[asset_class]
            num_assets_to_pick = max(1, int(num_holdings * target_pct))
            
            selected_assets = random.sample(assets_in_class, min(num_assets_to_pick, len(assets_in_class)))
            
            for asset in selected_assets:
                # Allocate a portion of the balance
                if len(holdings_created) < num_holdings - 1:
                    allocation_amount = remaining_balance * target_pct / len(selected_assets)
                else:
                    # Last holding gets remaining balance
                    allocation_amount = remaining_balance
                
                # Generate realistic price and quantity
                price = Decimal(random.uniform(*asset["price_range"]))
                quantity = Decimal(allocation_amount) / price
                cost_basis = price * Decimal(random.uniform(0.85, 1.05))  # +/- 15% from current price
                
                holding = Holding(
                    account_id=account.id,
                    symbol=asset["symbol"],
                    asset_class=asset_class,
                    sector=asset["sector"],
                    quantity=quantity,
                    price=price,
                    cost_basis=cost_basis,
                    dividend_yield=Decimal(asset["dividend"])
                )
                db.add(holding)
                holdings_created.append(holding)
                
                remaining_balance -= float(quantity * price)
                
                if remaining_balance <= 0 or len(holdings_created) >= num_holdings:
                    break
            
            if remaining_balance <= 0 or len(holdings_created) >= num_holdings:
                break
        
        accounts_created.append(account)
    
    db.commit()
    return accounts_created


def calculate_portfolio_metrics(user_id: str, db: Session) -> Dict:
    """Calculate aggregated portfolio metrics"""
    accounts = db.query(Account).filter_by(user_id=user_id).all()
    
    if not accounts:
        return None
    
    total_value = sum(float(acc.balance) for acc in accounts)
    
    # Calculate weighted YTD return
    weighted_return = sum(float(acc.balance * acc.ytd_return) for acc in accounts) / total_value if total_value > 0 else 0
    
    # Calculate asset allocation across all accounts
    asset_allocation = {}
    sector_allocation = {}
    
    for account in accounts:
        holdings = db.query(Holding).filter_by(account_id=account.id).all()
        for holding in holdings:
            market_value = float(holding.quantity * holding.price)
            
            # Asset class allocation
            asset_allocation[holding.asset_class] = asset_allocation.get(holding.asset_class, 0) + market_value
            
            # Sector allocation
            if holding.sector:
                sector_allocation[holding.sector] = sector_allocation.get(holding.sector, 0) + market_value
    
    # Convert to percentages
    asset_allocation_pct = {k: (v / total_value * 100) for k, v in asset_allocation.items()}
    sector_allocation_pct = {k: (v / total_value * 100) for k, v in sector_allocation.items()}
    
    # Calculate top holdings
    all_holdings = []
    for account in accounts:
        holdings = db.query(Holding).filter_by(account_id=account.id).all()
        for holding in holdings:
            market_value = float(holding.quantity * holding.price)
            gain_loss_pct = ((float(holding.price) - float(holding.cost_basis)) / float(holding.cost_basis) * 100) if holding.cost_basis > 0 else 0
            all_holdings.append({
                "symbol": holding.symbol,
                "asset_class": holding.asset_class,
                "sector": holding.sector,
                "market_value": market_value,
                "allocation_pct": (market_value / total_value * 100),
                "gain_loss_pct": gain_loss_pct
            })
    
    top_holdings = sorted(all_holdings, key=lambda x: x["market_value"], reverse=True)[:5]
    
    # Calculate risk score based on asset allocation
    risk_weights = {"Stock": 3, "ETF": 2, "Bond": 1, "Cash": 0}
    weighted_risk = sum(asset_allocation_pct.get(k, 0) * v for k, v in risk_weights.items())
    risk_score = min(100, weighted_risk / 3)  # Normalize to 0-100
    
    return {
        "total_value": total_value,
        "ytd_return": weighted_return,
        "asset_allocation": asset_allocation_pct,
        "sector_allocation": sector_allocation_pct,
        "top_holdings": top_holdings,
        "risk_score": risk_score,
        "accounts_count": len(accounts),
        "cash_percentage": asset_allocation_pct.get("Cash", 0)
    }
