let historyChart = null;
let currentRange = "30m";

async function loadHistory() {

    const response = await fetch(`/api/history?range=${currentRange}`);
    const data = await response.json();

    const labels = data.map(item =>
        new Date(item.timestamp * 1000).toLocaleTimeString()
    );

    const pv = data.map(item => item.pv_power);
    const house = data.map(item => item.house_load);
    const gridImport = data.map(item => item.grid_import);
    const gridExport = data.map(item => item.grid_export);

    if (!historyChart) {

        historyChart = new Chart(
            document.getElementById("historyChart"),
            {
                type: "line",

                data: {

                    labels: labels,

                    datasets: [

                        {
                            label: "PV-tuotanto",
                            data: pv
                        },

                        {
                            label: "Talon kulutus",
                            data: house
                        },

                        {
                            label: "Verkosta osto",
                            data: gridImport
                        },

                        {
                            label: "Verkkoon vienti",
                            data: gridExport
                        }

                    ]
                },

                options: {

                    responsive: true,
                    animation: false,

                    interaction: {
                        intersect: false,
                        mode: "index"
                    },

                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            }
        );

    } else {

        historyChart.data.labels = labels;

        historyChart.data.datasets[0].data = pv;
        historyChart.data.datasets[1].data = house;
        historyChart.data.datasets[2].data = gridImport;
        historyChart.data.datasets[3].data = gridExport;

        historyChart.update("none");
    }
}

loadHistory();

setInterval(loadHistory, 10000);

document.querySelectorAll(".history-range").forEach(button => {

    button.addEventListener("click", () => {

        document.querySelectorAll(".history-range").forEach(b =>
            b.classList.remove("active")
        );

        button.classList.add("active");

        currentRange = button.dataset.range;

        loadHistory();

    });

});
