document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("preferences-form");
    const recommendationDiv = document.getElementById("recommendation-summary");

    form.addEventListener("submit", async function (event) {
        event.preventDefault(); // Prevent the default form submission

        const formData = {
            income: parseFloat(document.getElementById("income").value),
            expenses: parseFloat(document.getElementById("expenses").value),
            savings: parseFloat(document.getElementById("savings").value),
            investments: parseFloat(document.getElementById("investments").value),
            debt: parseFloat(document.getElementById("debt").value),
            risk_tolerance: document.getElementById("risk-tolerance").value
        };

        try {
            const response = await fetch("/ai_generated_adjustments", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error("Network response was not ok");

            const result = await response.json();
            
            if (result.error) {
                recommendationDiv.innerHTML = `<p style="color:red;">${result.error}</p>`;
            } else {
                recommendationDiv.innerHTML = `
                    <div class="recommendation-header">
                        <i class="fas fa-lightbulb"></i>
                        <h3>AI Recommendations</h3>
                    </div>
                    <div class="recommendation-content">
                        <p><i class="fas fa-chart-pie"></i> <strong>Investment Strategy:</strong> ${result.investment_strategy}</p>
                        <p><i class="fas fa-piggy-bank"></i> <strong>Optimal Savings Plan:</strong> ${result.savings_plan}</p>
                        <p><i class="fas fa-hand-holding-usd"></i> <strong>Debt Repayment Strategy:</strong> ${result.debt_strategy}</p>
                        <p><i class="fas fa-chart-line"></i> <strong>Projected Growth:</strong> SGD ${result.projected_growth}</p>
                    </div>
                `;
            }
            recommendationDiv.style.display = "block";
            recommendationDiv.scrollIntoView({ behavior: "smooth" });
        } catch (error) {
            recommendationDiv.innerHTML = `<p style="color:red;">Error fetching recommendations. Try again.</p>`;
            console.error("Fetch error:", error);
        }
    });
});
