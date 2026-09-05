async function updateDashboard() {

    try {

        const response = await fetch("/api/status");
        const data = await response.json();

        const summary = data.summary || {};
        const meter = data.energy_meter || {};
        const inverters = data.inverters || {};

        document.getElementById("pv_power").textContent =
            (summary.pv_power ?? 0).toFixed(0) + " W";

        document.getElementById("load_power").textContent =
            (summary.house_load ?? 0).toFixed(0) + " W";

        document.getElementById("grid_import").textContent =
            (summary.grid_import ?? 0).toFixed(0) + " W";

        document.getElementById("grid_export").textContent =
            (summary.grid_export ?? 0).toFixed(0) + " W";

        document.getElementById("updated").textContent =
            new Date().toLocaleTimeString();


        // =========================
        // Invertterit
        // =========================

        let html = "";

        for (const [name, inv] of Object.entries(inverters)) {

            html += `
            <div class="card">
                <h3>${name}</h3>

                <div>
                    Power: ${(inv.power ?? 0).toFixed(0)} W
                </div>

                <div>
                    Today: ${((inv.day_yield ?? 0) / 1000).toFixed(2)} kWh
                </div>

                <div>
                    Total: ${(() => {

                        const total = (inv.total_yield ?? 0) / 1000;

                        if (total >= 1000) {

                            return `${(total / 1000).toLocaleString("fi-FI", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            })} MWh`;

                        }

                        return `${total.toLocaleString("fi-FI", {
                            minimumFractionDigits: 1,
                            maximumFractionDigits: 1
                        })} kWh`;

                    })()}
                </div>

            </div>`;
        }

        document.getElementById("inverters").innerHTML = html;


        // =========================
        // Vaiheet
        // =========================

        for (let i = 1; i <= 3; i++) {

            const voltage = meter[`phase${i}_voltage`] ?? 0;
            const current = meter[`phase${i}_current`] ?? 0;
            const power = meter[`phase${i}_power`] ?? 0;

            document.getElementById(`phase${i}`).innerHTML = `
                <h3>L${i}</h3>
                <div>${voltage.toFixed(1)} V</div>
                <div>${current.toFixed(2)} A</div>
                <div>${power.toFixed(0)} W</div>
            `;
        }

    } catch (error) {

        console.error("Dashboard update failed:", error);

    }
}


// =========================
// Elli / EVCC
// =========================

async function updateElli() {

    try {

        const response = await fetch("/api/evcc");

        if (!response.ok) {
            throw new Error("EVCC API error");
        }

        const data = await response.json();

        // =========================
        // Yhteys
        // =========================

        document.getElementById("elli-status").textContent =
            data.connected
                ? "Yhdistetty"
                : "Ei yhdistetty";


        // =========================
        // Lataus
        // =========================

        document.getElementById("elli-charging").textContent =
            data.charging
                ? "Lataa"
                : "Ei lataa";


        // =========================
        // Latausteho
        // =========================

        document.getElementById("elli-power").textContent =
            (Number(data.charge_power || 0) / 1000).toFixed(1) + " kW";


        // =========================
        // Käytössä
        // =========================

        document.getElementById("elli-enabled").textContent =
            data.enabled
                ? "Kyllä"
                : "Ei";


        // =========================
        // Ohjaustila
        // =========================

        const modeElement =
            document.getElementById("elli-mode");

        switch (data.mode) {

            case "pv":
                modeElement.textContent = "PV";
                break;

            case "now":
                modeElement.textContent = "Nyt";
                break;

            case "off":
                modeElement.textContent = "Pois";
                break;

            default:
                modeElement.textContent =
                    data.mode || "--";
        }


        // =========================
        // Aktiivisen ohjaustilan korostus
        // =========================

        document.querySelectorAll(".elli-mode-button").forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.mode === data.mode
            );

        });


        // =========================
        // Latausenergia
        // =========================

        document.getElementById("elli-energy").textContent =
            (Number(data.charged_energy || 0) / 1000).toFixed(2) + " kWh";

        // =========================
        // Aurinkoenergian osuus
        // =========================

        const solarElement =
            document.getElementById("elli-solar-percentage");

        solarElement.textContent =
            Number(data.solar_percentage ?? 0).toFixed(0) + " %";


    } catch (error) {

        console.error("Elli update failed:", error);

        document.getElementById("elli-status").textContent =
            "Ei yhteyttä";

        document.getElementById("elli-charging").textContent =
            "--";

        document.getElementById("elli-power").textContent =
            "--";

        document.getElementById("elli-enabled").textContent =
            "--";

        document.getElementById("elli-mode").textContent =
            "--";

        document.getElementById("elli-energy").textContent =
            "--";

        document.getElementById("elli-solar-percentage").textContent =
            "--";
    }
}

// =========================
// LKV / Heater control
// =========================

async function updateHeater() {

    try {

        const response = await fetch("/api/status");

        if (!response.ok) {
            throw new Error("Heater status API error");
        }

        const data = await response.json();

        const resol = data.resol || {};
        const spot = data.spot_price || {};
        const heater = data.heater_control || {};

        const controllerPower =
            Number(heater.controller_power);

        const controllerReason =
            heater.controller_reason || "UNKNOWN";


        // =========================
        // Vastustehon näyttö
        // =========================

        document.getElementById(
            "heater-power"
        ).textContent =
            Number.isFinite(controllerPower)
                ? controllerPower.toFixed(0) + " W"
                : "--";


        // =========================
        // Lämpötila
        // =========================

        const temperature =
            Number(resol["LKV 500l"]);

        document.getElementById("heater-temperature").textContent =
            Number.isFinite(temperature)
                ? temperature.toFixed(1) + " °C"
                : "--";


        // =========================
        // Spot-hinta
        // =========================

        const spotPrice =
            Number(spot.current);

        document.getElementById("heater-spot-price").textContent =
            Number.isFinite(spotPrice)
                ? spotPrice.toFixed(3) + " snt/kWh"
                : "--";


        // =========================
        // Hintaraja
        // =========================

        const priceLimit =
            Number(heater.spot_price_limit);

        const priceInput =
            document.getElementById("heater-price-limit");

        if (
            Number.isFinite(priceLimit)
            && document.activeElement !== priceInput
        ) {
            priceInput.value =
                priceLimit.toFixed(1);
        }


        // =========================
        // Maksimi vastusteho
        // =========================

        const maxPower =
            Number(heater.max_power);

        const maxPowerInput =
            document.getElementById(
                "heater-max-power"
            );

        if (
            Number.isFinite(maxPower)
            && document.activeElement !== maxPowerInput
        ) {
            maxPowerInput.value =
                maxPower.toFixed(0);
        }

        // =========================
        // Ohjaustila
        // =========================

        const mode =
            heater.mode || "off";

        const modeElement =
            document.getElementById("heater-mode");

        switch (mode) {

            case "off":
                modeElement.textContent = "Pois";
                break;

            case "pv":
                modeElement.textContent = "PV";
                break;

            case "pv_price":
                modeElement.textContent = "PV + hinta";
                break;

            case "on":
                modeElement.textContent = "Päällä";
                break;

            default:
                modeElement.textContent = mode;
        }


        // =========================
        // Aktiivisen napin korostus
        // =========================

        document.querySelectorAll(
            ".heater-mode-button"
        ).forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.mode === mode
            );

        });


        // =========================
        // Controllerin todellinen tila
        // =========================

        const statusElement =
            document.getElementById("heater-status");

        switch (controllerReason) {

        case "EXPORT":
            statusElement.textContent =
                "PV-ylijäämä – tehoa lisätään";
            break;

        case "IMPORT":
            statusElement.textContent =
                "Verkko-osto – tehoa vähennetään";
            break;

        case "DEADBAND":
            statusElement.textContent =
                "Tasapainossa";
            break;

        case "HOLD":
            statusElement.textContent =
                "Teho pidetään";
            break;

        case "LIMIT":
            statusElement.textContent =
                "Tehoraja";
            break;

        case "SPOT_HIGH":
            statusElement.textContent =
                "Spot-hinta yli rajan";
            break;

        case "DHW_MAX":
            statusElement.textContent =
                "Lämpötilaraja saavutettu";
            break;

        case "OFF":
            statusElement.textContent =
                "Pois käytöstä";
            break;

        case "ON":
            statusElement.textContent =
                "Pakotettu päälle";
            break;

        case "MODE_ERROR":
            statusElement.textContent =
                "Ohjaustilavirhe";
            break;

        case "UNKNOWN":
            statusElement.textContent =
                "Controllerin tila ei tiedossa";
            break;

        default:
            statusElement.textContent =
                controllerReason;
    }

    } catch (error) {

        console.error(
            "Heater update failed:",
            error
        );

        document.getElementById(
            "heater-temperature"
        ).textContent = "--";

        document.getElementById(
            "heater-spot-price"
        ).textContent = "--";

        document.getElementById(
            "heater-mode"
        ).textContent = "--";

        document.getElementById(
            "heater-status"
        ).textContent = "Ei yhteyttä";

        document.getElementById(
            "heater-power"
        ).textContent = "--";
    }

}

// =========================
// Energiatilastot
// =========================

async function updateEnergyStats() {

    try {

        const response = await fetch("/api/energy_stats");

        if (!response.ok) {
            throw new Error("Energy stats API error");
        }

        const stats = await response.json();

        document.getElementById("pv-day-yield").textContent =
            `${(stats.pv_day_yield ?? 0).toFixed(2)} kWh`;

        document.getElementById("house-energy").textContent =
            `${(stats.house_load ?? 0).toFixed(2)} kWh`;

        document.getElementById("grid-import-energy").textContent =
            `${(stats.grid_import ?? 0).toFixed(2)} kWh`;

        document.getElementById("grid-export-energy").textContent =
            `${(stats.grid_export ?? 0).toFixed(2)} kWh`;

        document.getElementById("self-sufficiency").textContent =
            `${(stats.self_sufficiency ?? 0).toFixed(1)} %`;

    } catch (error) {

        console.error("Energy stats update failed:", error);

    }
}

// =========================
// Elli / EVCC ohjaus
// =========================

async function setElliMode(mode) {

    const buttons = document.querySelectorAll(".elli-mode-button");

    // Estetään tuplapainallukset komennon aikana
    buttons.forEach(button => {
        button.disabled = true;
    });

    try {

        const response = await fetch("/api/evcc/mode", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mode: mode
            })
        });

        if (!response.ok) {
            throw new Error("EVCC mode change failed");
        }

        // Haetaan uusi tila heti
        await updateElli();

    } catch (error) {

        console.error("Elli mode change failed:", error);

        alert("Ellin ohjaus epäonnistui.");

    } finally {

        buttons.forEach(button => {
            button.disabled = false;
        });
    }
}


// Painikkeet

document.querySelectorAll(".elli-mode-button").forEach(button => {

    button.addEventListener("click", () => {

        const mode = button.dataset.mode;

        setElliMode(mode);

    });

});


// =========================
// Heater controls
// =========================

document.querySelectorAll(
    ".heater-mode-button"
).forEach(button => {

    button.addEventListener(
        "click",
        () => {

            const mode =
                button.dataset.mode;

            setHeaterMode(mode);

        }
    );

});

document.getElementById(
    "heater-price-save"
).addEventListener(
    "click",
    saveHeaterPriceLimit
);

document.getElementById(
    "heater-max-power-save"
).addEventListener(
    "click",
    saveHeaterMaxPower
);

// =========================
// Heater mode
// =========================

async function setHeaterMode(mode) {

    const buttons =
        document.querySelectorAll(
            ".heater-mode-button"
        );

    buttons.forEach(button => {
        button.disabled = true;
    });

    try {

        const response = await fetch(
            "/api/heater/control",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    mode: mode
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Heater mode change failed"
            );
        }

        await updateHeater();

    } catch (error) {

        console.error(
            "Heater mode change failed:",
            error
        );

        alert(
            "LKV-ohjauksen tilan vaihto epäonnistui."
        );

    } finally {

        buttons.forEach(button => {
            button.disabled = false;
        });

    }

}


// =========================
// Heater spot price limit
// =========================

async function saveHeaterPriceLimit() {

    const input =
        document.getElementById(
            "heater-price-limit"
        );

    const button =
        document.getElementById(
            "heater-price-save"
        );

    const value =
        Number(input.value);

    if (!Number.isFinite(value)) {
        alert("Anna kelvollinen hintaraja.");
        return;
    }

    button.disabled = true;

    try {

        const response = await fetch(
            "/api/heater/control",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    spot_price_limit: value
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Price limit save failed"
            );
        }

        await updateHeater();

    } catch (error) {

        console.error(
            "Heater price limit save failed:",
            error
        );

        alert(
            "Hintarajan tallennus epäonnistui."
        );

    } finally {

        button.disabled = false;

    }

}

// =========================
// Heater max power
// =========================

async function saveHeaterMaxPower() {

    const input =
        document.getElementById(
            "heater-max-power"
        );

    const button =
        document.getElementById(
            "heater-max-power-save"
        );

    const value =
        Number(input.value);

    if (
        !Number.isFinite(value)
        || value < 0
        || value > 6000
    ) {
        alert(
            "Anna kelvollinen vastusteho 0–6000 W."
        );
        return;
    }

    button.disabled = true;

    try {

        const response = await fetch(
            "/api/heater/control",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    max_power: value
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Max power save failed"
            );
        }

        await updateHeater();

    } catch (error) {

        console.error(
            "Heater max power save failed:",
            error
        );

        alert(
            "Maksimivastustehon tallennus epäonnistui."
        );

    } finally {

        button.disabled = false;
    }
}


// =========================
// Käynnistys
// =========================

updateDashboard();
updateElli();
updateEnergyStats();
updateHeater();

setInterval(updateDashboard, 1000);
setInterval(updateElli, 5000);
setInterval(updateEnergyStats, 60000);
setInterval(updateHeater, 5000);
