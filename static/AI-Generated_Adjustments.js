document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("preferences-form");
    const recommendationDiv = document.getElementById("recommendation-summary");

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        // Collect form data
        const formData = {
            income: document.getElementById("income").value,
            expenses: document.getElementById("expenses").value,
            savings: document.getElementById("savings").value,
            investments: document.getElementById("investments").value,
            debt: document.getElementById("debt").value,
            risk_tolerance: document.getElementById("risk-tolerance").value,
            investment_goal: document.getElementById("investment-goal").value
        };

        try {
            const response = await fetch("//ai_generated_adjustments", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error("Network response was not ok");

            const result = await response.json();

            recommendationDiv.innerHTML = `
                <h3>AI Recommendations</h3>
                <p><strong>Investment Strategy:</strong> ${result.investment_strategy}</p>
                <p><strong>Optimal Savings Plan:</strong> ${result.savings_plan}</p>
                <p><strong>Debt Repayment Strategy:</strong> ${result.debt_strategy}</p>
                <p><strong>Projected Growth:</strong> ${result.projected_growth}%</p>
            `;
        } catch (error) {
            recommendationDiv.innerHTML = `<p style="color:red;">Error fetching recommendations.</p>`;
            console.error("Fetch error:", error);
        }
    });
});
