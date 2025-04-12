def simulate_retirement(current_age, retirement_age, monthly_income, monthly_expenses, 
                        monthly_savings, investment_strategy, investment_increase=0,
                        career_switch_impact=0, purchase_amount=0, career_switch_age=0, purchase_age=0,
                        retirement_investment_strategy="conservative"):
    # Input validations
    if not (18 <= current_age <= 100):
        raise ValueError("Current Age must be between 18 and 100")
    
    if not (18 <= retirement_age <= 100):
        raise ValueError("Retirement Age must be between 18 and 100")
    
    if retirement_age <= current_age:
        raise ValueError("Retirement Age must be greater than Current Age")
    
    valid_strategies = ["conservative", "balanced", "aggressive"]
    if investment_strategy not in valid_strategies:
        raise ValueError("Investment Strategy must be Conservative, Balanced or Aggressive")
    
    if retirement_investment_strategy not in valid_strategies:
        raise ValueError("Investment Strategy After Retirement must be Conservative, Balanced or Aggressive")
    
    if monthly_income < 0:
        raise ValueError("Monthly Income cannot be negative")
    
    if monthly_expenses < 0:
        raise ValueError("Monthly Expenses cannot be negative")
    
    if monthly_savings < 0:
        raise ValueError("Monthly Savings cannot be negative")
    
    if purchase_amount < 0:
        raise ValueError("Purchase Amount for House cannot be negative")
    
    if career_switch_age != 0 and not (18 <= career_switch_age <= 100):
        raise ValueError("Age of Career Switch must be between 18 and 100")
    
    if purchase_age != 0 and not (18 <= purchase_age <= 100):
        raise ValueError("Age of House Purchase must be between 18 and 100")

    annual_return_rates = {
        "conservative": 0.04,  # 4%
        "balanced": 0.06,      # 6%
        "aggressive": 0.08     # 8%
    }
    
    annual_return = annual_return_rates.get(investment_strategy, 0.06)
    retirement_annual_return = annual_return_rates.get(retirement_investment_strategy, 0.04)
    
    working_years = retirement_age - current_age
    
    yearly_results = []
    total_savings = 0
    annual_savings = monthly_savings * 12
    annual_income = monthly_income * 12
    annual_expenses = monthly_expenses * 12
    
    for year in range(working_years):
        current_user_age = current_age + year
        
        if career_switch_impact != 0 and career_switch_age != 0 and current_user_age == career_switch_age:
            annual_income += career_switch_impact
            annual_savings = (annual_income / 12 - monthly_expenses) * 12
            
        if investment_increase > 0:
            current_return = annual_return * (1 + (investment_increase / 100) * (year / working_years))
        else:
            current_return = annual_return
        
        total_savings += annual_savings
        
        investment_return = total_savings * current_return
        total_savings += investment_return
        
        if purchase_amount > 0 and purchase_age != 0 and current_user_age == purchase_age:
            total_savings -= purchase_amount
        
        yearly_results.append({
            "age": current_user_age,
            "savings": round(total_savings, 2),
            "annual_income": round(annual_income, 2),
            "annual_expenses": round(annual_expenses, 2),
            "investment_return": round(investment_return, 2),
            "annual_savings": round(annual_savings, 2)
        })
    
    retirement_years = 30  # Suppose simulation for 30 years after retirement
    retirement_annual_expenses = annual_expenses * 0.8  # Suppose 80% of pre-retirement expenses
    retirement_results = []
    
    retirement_savings = total_savings
    
    for year in range(retirement_years):
        retirement_return = retirement_savings * retirement_annual_return
        retirement_savings = retirement_savings + retirement_return - retirement_annual_expenses
        
        retirement_results.append({
            "age": retirement_age + year,
            "savings": round(retirement_savings, 2),
            "annual_expenses": round(retirement_annual_expenses, 2),
            "investment_return": round(retirement_return, 2)
        })
        
        if retirement_savings <= 0:
            break
    
    return {
        "working_phase": yearly_results,
        "retirement_phase": retirement_results,
        "total_retirement_savings": yearly_results[-1]["savings"] if yearly_results else 0,
        "retirement_funds_depletion_age": retirement_age + year if retirement_savings <= 0 else None,
        "summary": generate_summary(yearly_results, retirement_results, retirement_age)
    }

def generate_summary(working_results, retirement_results, retirement_age):
    retirement_savings = working_results[-1]["savings"] if working_results else 0
    retirement_years_covered = len(retirement_results)
    
    messages = []
    
    if retirement_savings <= 0:
        messages.append("Warning: Your savings may not be enough before retirement. Consider increasing monthly savings or adjusting investment strategy.")
    elif retirement_years_covered < 20:
        messages.append(f"Your retirement savings may only support {retirement_years_covered} years. Consider increasing savings before retirement.")
    else:
        messages.append(f"Your retirement plan looks solid! Your savings can cover {retirement_years_covered} years or more.")
    
    total_investment_returns = sum(year["investment_return"] for year in working_results)
    
    if retirement_savings > 0:
        roi_percentage = (total_investment_returns / retirement_savings * 100)
        messages.append(f"Your investment return is approximately {roi_percentage:.1f}% of your total retirement savings.")
    
    for i in range(1, len(working_results)):
        if working_results[i]["savings"] < working_results[i-1]["savings"]:
            messages.append("Warning: Large purchases (e.g., house) may significantly impact your savings growth. Consider increasing monthly savings to compensate for this impact.")
            break
    
    return messages
