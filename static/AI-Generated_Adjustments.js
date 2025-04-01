document.getElementById('preferences-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent page refresh

    // Get the values from input fields
    const riskTolerance = document.getElementById('risk-tolerance').value;
    const investmentGoal = document.getElementById('investment-goal').value;
    const monthlySavings = parseFloat(document.getElementById('monthly-savings').value) || 0;

    // Simulate AI-generated financial recommendations (could be based on real algorithms)
    let aiSuggestions = [];

    // Risk tolerance-based investment adjustments
    if (riskTolerance === 'low') {
        aiSuggestions.push('Invest 50% in Bonds, 50% in Savings Account.');
    } else if (riskTolerance === 'medium') {
        aiSuggestions.push('Invest 60% in Balanced Mutual Funds, 40% in Bonds.');
    } else if (riskTolerance === 'high') {
        aiSuggestions.push('Invest 80% in Stocks, 20% in High-Risk ETFs.');
    }

    // Simulate adjusting monthly savings (AI suggests an increase if necessary)
    if (monthlySavings < 3000) {
        aiSuggestions.push('Consider increasing monthly savings to at least SGD 3000 for better long-term growth.');
    }

    // Display the recommendations
    document.getElementById('recommendation-summary').innerHTML = aiSuggestions.join('<br/>');

    // Simulate a graph or chart update (e.g., Investment Growth Simulation)
    const recommendationChart = document.getElementById('recommendation-chart');
    recommendationChart.style.backgroundColor = '#007BFF'; // Change based on results

    // Optional: You can integrate Chart.js or D3.js to create a more dynamic graph
});
