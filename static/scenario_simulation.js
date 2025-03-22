document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('scenario-form');
    const resultSummary = document.getElementById('result-summary');
    const resultChart = document.getElementById('result-chart');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = {
            current_age: parseInt(document.getElementById('current-age').value),
            retirement_age: parseInt(document.getElementById('retirement-age').value),
            monthly_income: parseFloat(document.getElementById('monthly-income').value),
            monthly_expenses: parseFloat(document.getElementById('monthly-expenses').value),
            monthly_savings: parseFloat(document.getElementById('monthly-savings').value),
            investment_strategy: document.getElementById('investment-strategy').value,
            retirement_investment_strategy: document.getElementById('retirement-investment-strategy').value,
            investment_increase: parseFloat(document.getElementById('investment-increase').value || 0),
            career_switch_impact: parseFloat(document.getElementById('career-switch-impact').value || 0),
            career_switch_age: parseInt(document.getElementById('career-switch-age').value || 0),
            purchase_amount: parseFloat(document.getElementById('purchase-amount').value || 0),
            purchase_age: parseInt(document.getElementById('purchase-age').value || 0)
        };
        
        resultSummary.innerHTML = '<div class="loading">Simulating, please wait...</div>';
        document.getElementById('simulation-results').classList.add('show');
        
        fetch('/run_simulation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data);
        })
        .catch(error => {
            console.error('Error:', error);
            resultSummary.innerHTML = '<div class="error">Something went wrong, please try again.</div>';
        });
    });
    
    function displayResults(data) {
        resultSummary.innerHTML = '';
        resultChart.innerHTML = '';
        
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'summary-container';
        
        summaryDiv.innerHTML = `
            <h3>Simulation Result Summary</h3>
            <div class="key-stats">
                <div class="stat">
                    <span class="stat-value">${formatCurrency(data.total_retirement_savings)}</span>
                    <span class="stat-label">Total Retirement Savings</span>
                </div>
                <div class="stat">
                    <span class="stat-value">${data.retirement_funds_depletion_age || '90+'}</span>
                    <span class="stat-label">Estimated Funds Depletion Age</span>
                </div>
            </div>
            <div class="result-messages">
                ${data.summary.map(msg => `<p>➢ ${msg}</p>`).join('')}
            </div>
        `;
        
        resultSummary.appendChild(summaryDiv);
        
        createChart(data);
    }
    
    function createChart(data) {
        const chartCanvas = document.createElement('canvas');
        chartCanvas.id = 'financial-chart';
        resultChart.appendChild(chartCanvas);
        
        const workingPhase = data.working_phase;
        const retirementPhase = data.retirement_phase;
        
        const labels = [...workingPhase.map(d => d.age), ...retirementPhase.map(d => d.age)];
        const savingsData = [...workingPhase.map(d => d.savings), ...retirementPhase.map(d => d.savings)];
        
        const retirementIndex = workingPhase.length - 1;
        
        new Chart(chartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Savings (SGD)',
                    data: savingsData,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Financial Growth Forecast'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += formatCurrency(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                xMin: retirementIndex,
                                xMax: retirementIndex,
                                borderColor: 'rgb(255, 99, 132)',
                                borderWidth: 2,
                                label: {
                                    display: true,
                                    content: 'Retirement',
                                    position: 'top'
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatCurrency(value, false);
                            }
                        }
                    }
                }
            }
        });
    }
    
    function formatCurrency(value, includeSymbol = true) {
        if (value === null || value === undefined || isNaN(value)) {
            return includeSymbol ? 'SGD 0.00' : '0';
        }
        
        const formatter = new Intl.NumberFormat('en-SG', {
            style: includeSymbol ? 'currency' : 'decimal',
            currency: 'SGD',
            minimumFractionDigits: includeSymbol ? 2 : 0,
            maximumFractionDigits: includeSymbol ? 2 : 0,
        });
        
        return formatter.format(value);
    }
    
    function initializeForm() {
        document.getElementById('current-age').value = 30;
        document.getElementById('retirement-age').value = 65;
        document.getElementById('monthly-income').value = 5000;
        document.getElementById('monthly-expenses').value = 3000;
        document.getElementById('monthly-savings').value = 1000;
    }
    
    initializeForm();
});