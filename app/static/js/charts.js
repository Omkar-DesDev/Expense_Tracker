function drawCharts(monthlyData, categoryData){
  const months = monthlyData.map(m=>m.month);
  const totals = monthlyData.map(m=>m.total);

  const ctx = document.getElementById('monthlyChart');
  if(ctx){
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: [{label: 'Monthly Spending', data: totals, tension:0.3}]
      },
      options: {responsive:true}
    });
  }

  const cats = categoryData.map(c=>c.category);
  const catTotals = categoryData.map(c=>c.total);
  const ctx2 = document.getElementById('categoryChart');
  if(ctx2){
    new Chart(ctx2, {
      type: 'pie',
      data: {labels: cats, datasets:[{data: catTotals}]},
      options: {responsive:true}
    });
  }
}
