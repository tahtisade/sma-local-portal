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
// EVCC
// =========================

async function updateElli() {

    try {

        const response = await fetch("/api/evcc");
        const controlResponse = await fetch("/api/evcc/control");

        if (!response.ok) {
            throw new Error("EVCC API error");
        }

        if (!controlResponse.ok) {
            throw new Error("Elli control API error");
        }

        const data = await response.json();
        const control = await controlResponse.json();

        // =========================
        // Elli hinta-asetukset
        // =========================

        const priceLimit =
            Number(control.spot_price_limit);

        const priceLimitInput =
            document.getElementById("elli-price-limit");

        const priceStartInput =
            document.getElementById("elli-price-start");

        const priceEndInput =
            document.getElementById("elli-price-end");

        if (document.activeElement !== priceLimitInput) {
            priceLimitInput.value =
                Number.isFinite(priceLimit)
                    ? priceLimit.toFixed(1)
                    : "";
        }

        if (
            document.activeElement !== priceStartInput &&
            !priceStartInput.dataset.dirty
        ) {
            priceStartInput.value =
                control.price_start || "00:00";
        }

        if (
            document.activeElement !== priceEndInput &&
            !priceEndInput.dataset.dirty
        ) {
            priceEndInput.value =
                control.price_end || "00:00";
        }

        priceTimeSynced("elli", control.price_start, control.price_end);

        document.getElementById("evcc-title").textContent =
            data.title || "EVCC";

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
        // Todellinen latausteho
        // =========================

        if (data.actual_charge_power_error) {
            document.getElementById("elli-actual-power").textContent = "--";
        } else {
            document.getElementById("elli-actual-power").textContent =
                (Number(data.actual_charge_power || 0) / 1000).toFixed(2) + " kW";
        }


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

        switch (control.mode) {

            case "pv":
                modeElement.textContent = "PV";
                break;

            case "price":
                modeElement.textContent = "Hinta";
                break;

            case "now":
                modeElement.textContent = "Nyt";
                break;

            case "off":
                modeElement.textContent = "Pois";
                break;

            default:
                modeElement.textContent =
                    control.mode || "--";
        }


        // =========================
        // Aktiivisen ohjaustilan korostus
        // =========================

        document.querySelectorAll(".elli-mode-button").forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.mode === control.mode
            );

        });


        // =========================
        // Latausenergia
        // =========================

        document.getElementById("elli-energy").textContent =
            (Number(data.charged_energy || 0) / 1000).toFixed(2) + " kWh";

        document.getElementById("elli-daily-energy").textContent =
            Number(data.actual_charge_daily_energy || 0).toFixed(2) + " kWh";

        document.getElementById("elli-total-energy").textContent =
            Number(data.actual_charge_total_energy || 0).toFixed(2) + " kWh";

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

        document.getElementById("elli-daily-energy").textContent =
            "--";

        document.getElementById("elli-total-energy").textContent =
            "--";

        document.getElementById("elli-actual-power").textContent =
            "--";

        document.getElementById("elli-solar-percentage").textContent =
            "--";
    }
}

// =========================
// PV surplus load control
// =========================

// Optional measured load data, independent of the commanded heater power.
function updateHeaterMeter(meter, apiFailed = false) {
    if (!apiFailed) {
        document.querySelectorAll(".heater-meter-row").forEach(row => {
            row.hidden = !meter?.enabled;
        });
    }
    const format = (value, unit) =>
        typeof value === "number" && Number.isFinite(value)
            ? value.toLocaleString("fi-FI", {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            }) + " " + unit : "--";
    document.getElementById("heater-measured-power").textContent =
        format(apiFailed ? null : meter?.power_kw, "kW");
    document.getElementById("heater-measured-daily").textContent =
        format(apiFailed ? null : meter?.daily_energy_kwh, "kWh");
    document.getElementById("heater-measured-total").textContent =
        format(apiFailed ? null : meter?.total_energy_kwh, "kWh");
    const label = document.getElementById("heater-daily-label");
    label.textContent = meter?.daily_energy_partial
        ? "Energia tänään (vajaa)" : "Energia tänään (arvio)";
    label.title = "Lasketaan kokonaisenergian muutoksesta Suomen vuorokauden mukaan. " +
        "Vajaa lukema alkaa seurannan aloituksesta. Vuorokauden raja on likimääräinen.";
    document.getElementById("heater-meter-status").textContent = apiFailed
        ? "Ei yhteyttä portaaliin"
        : meter?.status === "live" ? "Mittaus käytössä"
        : meter?.connected ? "Odotetaan tuoreita mittauksia" : "Ei yhteyttä";
}

async function updateHeater() {

    try {

        const response = await fetch("/api/status");

        if (!response.ok) {
            throw new Error("Heater status API error");
        }

        const data = await response.json();
        updateHeaterMeter(data.heater_meter);

        const resol = data.resol || {};
        const spot = data.spot_price || {};
        const heater = data.heater_control || {};

        const controllerPower =
            Number(heater.controller_power);

        const controllerReason =
            heater.controller_reason || "UNKNOWN";


        // =========================
        // Kuormatehon näyttö
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

        const temperatureElement =
            document.getElementById("heater-temperature");

        if (temperatureElement) {
            const temperature =
                Number(resol.temperature);

            temperatureElement.textContent =
                resol.temperature != null && Number.isFinite(temperature)
                  ? temperature.toFixed(1) + " °C"
                  : "--";
        }


        // =========================
        // Spot-hinta
        // =========================

        const spotPrice =
            Number(spot.current);

        document.getElementById("heater-spot-price").textContent =
            Number.isFinite(spotPrice)
                ? spotPrice.toFixed(3) + " snt/kWh"
                : "--";

        document.getElementById("elli-spot-price").textContent =
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
        // Hinta-tilan aika
        // =========================

        const priceStart =
            heater.price_start || "00:00";

        const priceEnd =
            heater.price_end || "06:00";

        const priceStartInput =
            document.getElementById(
                "heater-price-start"
            );

        const priceEndInput =
            document.getElementById(
                "heater-price-end"
            );

        if (
            document.activeElement !== priceStartInput &&
            !priceStartInput.dataset.dirty
        ) {
            priceStartInput.value =
                priceStart;
        }

        if (
            document.activeElement !== priceEndInput &&
            !priceEndInput.dataset.dirty
        ) {
            priceEndInput.value =
                priceEnd;
        }

        // =========================
        priceTimeSynced("heater", heater.price_start, heater.price_end);
        temperatureTargetSynced(heater.temperature_target);

        // Maksimi kuormateho
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

            case "price":
                modeElement.textContent = "Hinta";
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

        case "PRICE_TIME":
            statusElement.textContent =
                "Hinta – aikaikkunan ulkopuolella";
            break;

        case "PRICE_ON":
            statusElement.textContent =
                "Hinta – lämmitys päällä";
            break;

        case "DHW_MAX":
            statusElement.textContent =
                "Lämpötilatavoite saavutettu / lämpötilalukko";
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

        updateHeaterMeter(null, true);

        console.error(
            "Heater update failed:",
            error
        );

        const temperatureElement =
            document.getElementById("heater-temperature");

        if (temperatureElement) {
            temperatureElement.textContent = "--";
        }

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
// EVCC ohjaus
// =========================

async function setElliMode(mode) {

    const buttons = document.querySelectorAll(".elli-mode-button");

    // Estetään tuplapainallukset komennon aikana
    buttons.forEach(button => {
        button.disabled = true;
    });

    try {

        const response = await fetch("/api/evcc/control", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mode: mode
            })
        });

        if (!response.ok) {
            throw new Error("Elli control mode change failed");
        }

        // Haetaan uusi tila heti
        await updateElli();

    } catch (error) {

        console.error("Elli mode change failed:", error);

        alert("EVCC-ohjaus epäonnistui.");

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


// Elli hintarajan tallennus

document.getElementById("elli-price-save").addEventListener(
    "click",
    async () => {

        const button =
            document.getElementById("elli-price-save");

        const input =
            document.getElementById("elli-price-limit");

        const priceLimit =
            Number(input.value);

        if (!Number.isFinite(priceLimit)) {
            alert("Virheellinen hintaraja.");
            return;
        }

        button.disabled = true;

        try {

            const response = await fetch(
                "/api/evcc/control",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        spot_price_limit: priceLimit
                    })
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Elli price limit save failed"
                );
            }

            await updateElli();

        } catch (error) {

            console.error(
                "Elli price limit save failed:",
                error
            );

            alert(
                "Ellin hintarajan tallennus epäonnistui."
            );

        } finally {

            button.disabled = false;
        }
    }
);


// Elli hinta-tilan ajan tallennus

document.getElementById("elli-price-time-save").addEventListener(
    "click", () => savePriceTime("elli", "/api/evcc/control")
);

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

document
    .getElementById("heater-price-time-save")
    .addEventListener(
        "click",
        saveHeaterPriceTime
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
            "Kuorman ohjaustilan vaihto epäonnistui."
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

async function saveHeaterPriceTime() {
    await savePriceTime("heater", "/api/heater/control");
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
            "Anna kelvollinen kuormateho 0–6000 W."
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
            "Maksimikuormatehon tallennus epäonnistui."
        );

    } finally {

        button.disabled = false;
    }
}


// =========================
// Explicit unsaved/saved state for both price-time controls.
const priceTimeStates = new Map();

function priceTimeElements(prefix) {
    return {
        start: document.getElementById(prefix + "-price-start"),
        end: document.getElementById(prefix + "-price-end"),
        button: document.getElementById(prefix + "-price-time-save"),
        status: document.getElementById(prefix + "-price-time-status")
    };
}

function renderPriceTime(prefix) {
    const state = priceTimeStates.get(prefix);
    if (!state) return;
    const {start, end, button, status} = priceTimeElements(prefix);
    const dirty = state.saved ? start.value !== state.saved.start || end.value !== state.saved.end : state.edited;
    // Protect both fields from polling while one field contains an unsaved edit.
    start.dataset.dirty = end.dataset.dirty = dirty ? "true" : "";
    start.disabled = end.disabled = state.saving;
    button.disabled = state.saving || !dirty;
    button.textContent = state.saving ? "Tallennetaan…" : (dirty ? "Tallenna" : "Tallennettu");
    button.style.background = dirty ? "#fff4ce" : "#263b4a";
    button.style.color = dirty ? "#604400" : "#fff";
    button.style.border = "2px solid " + (dirty ? "#9c7200" : "#263b4a");
    button.style.opacity = "1";
    const active = state.saved ? "Käytössä " + state.saved.start + "–" + state.saved.end : "Tallennettua aikaa ei vielä saatu";
    status.textContent = state.saving ? "Tallennetaan…" :
        (state.error ? "Tallennus epäonnistui. " + active :
         (dirty ? "Tallentamatta · " + active : "Tallennettu · " + active));
    status.style.color = state.error ? "#a00000" : (dirty ? "#805900" : "#263b4a");
}

function priceTimeSynced(prefix, start, end) {
    const state = priceTimeStates.get(prefix);
    if (!state || state.saving || typeof start !== "string" || typeof end !== "string") return;
    state.saved = {start, end};
    renderPriceTime(prefix);
}

async function savePriceTime(prefix, url) {
    const state = priceTimeStates.get(prefix);
    if (!state || state.saving) return;
    const {start, end} = priceTimeElements(prefix);
    const value = {price_start: start.value, price_end: end.value};
    const valid = v => /^([01]\d|2[0-3]):[0-5]\d$/.test(v);
    if (!valid(value.price_start) || !valid(value.price_end)) {
        alert("Anna sekä alkamis- että päättymisaika.");
        return;
    }
    state.saving = true;
    state.error = false;
    renderPriceTime(prefix);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
        const response = await fetch(url, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(value), signal: controller.signal
        });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const result = await response.json();
        if (result.price_start !== value.price_start || result.price_end !== value.price_end) {
            throw new Error("Palvelin ei vahvistanut aika-asetusta");
        }
        state.saved = {start: result.price_start, end: result.price_end};
    } catch (error) {
        state.error = true;
        console.error("Price time save failed:", error);
    } finally {
        clearTimeout(timer);
        state.saving = false;
        renderPriceTime(prefix);
    }
}

for (const prefix of ["elli", "heater"]) {
    const {start, end, button} = priceTimeElements(prefix);
    if (!start || !end || !button) continue;
    priceTimeStates.set(prefix, {saved: null, saving: false, error: false, edited: false});
    const status = document.createElement("div");
    status.id = prefix + "-price-time-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.style.fontSize = "0.9em";
    status.style.marginTop = "0.4em";
    button.insertAdjacentElement("afterend", status);
    for (const input of [start, end]) {
        input.addEventListener("input", () => {
            priceTimeStates.get(prefix).error = false;
            priceTimeStates.get(prefix).edited = true;
            renderPriceTime(prefix);
        });
    }
    renderPriceTime(prefix);
}

window.addEventListener("beforeunload", event => {
    const pending = [...priceTimeStates.keys()].some(prefix => {
        const {start, end} = priceTimeElements(prefix);
        const state = priceTimeStates.get(prefix);
        return state.saving || (state.saved && (start.value !== state.saved.start || end.value !== state.saved.end));
    });
    if (pending || temperatureTargetState.saving || temperatureTargetDirty()) { event.preventDefault(); event.returnValue = ""; }
});


// Temperature target: polling never overwrites an unsaved edit.
const temperatureTargetState = {saved: null, edited: false, saving: false, error: false};
const temperatureTargetInput = document.getElementById("heater-temperature-target");
const temperatureTargetButton = document.getElementById("heater-temperature-target-save");
const temperatureTargetStatus = document.getElementById("heater-temperature-target-status");

function temperatureTargetDirty() {
    if (!temperatureTargetInput) return false;
    return temperatureTargetState.saved === null ? temperatureTargetState.edited :
        temperatureTargetInput.value.trim() === "" || Number(temperatureTargetInput.value) !== temperatureTargetState.saved;
}

function renderTemperatureTarget() {
    if (!temperatureTargetInput || !temperatureTargetButton || !temperatureTargetStatus) return;
    const state = temperatureTargetState;
    const dirty = temperatureTargetDirty();
    temperatureTargetInput.dataset.dirty = dirty ? "true" : "";
    temperatureTargetInput.disabled = state.saving;
    temperatureTargetButton.disabled = state.saving || !dirty || state.saved === null;
    temperatureTargetButton.textContent = state.saving ? "Tallennetaan…" : (dirty ? "Tallenna" : (state.saved === null ? "Odotetaan…" : "Tallennettu"));
    temperatureTargetButton.style.background = dirty ? "#fff4ce" : "#263b4a";
    temperatureTargetButton.style.color = dirty ? "#604400" : "#fff";
    temperatureTargetButton.style.border = "2px solid " + (dirty ? "#9c7200" : "#263b4a");
    temperatureTargetButton.style.opacity = "1";
    const active = state.saved === null ? "Tallennettua tavoitetta ei vielä saatu" :
        "Käytössä " + state.saved.toFixed(1) + " °C · jatkuu " + (state.saved - 2).toFixed(1) + " °C";
    temperatureTargetStatus.textContent = state.saving ? "Tallennetaan…" :
        (state.error ? "Tallennus epäonnistui. " + active :
         (dirty ? "Tallentamatta · " + active : (state.saved === null ? active : "Tallennettu · " + active)));
    temperatureTargetStatus.style.color = state.error ? "#a00000" : (dirty ? "#805900" : "#263b4a");
}

function temperatureTargetSynced(value) {
    if (!temperatureTargetInput || temperatureTargetState.saving || typeof value !== "number" || !Number.isFinite(value)) return;
    const dirty = temperatureTargetDirty();
    temperatureTargetState.saved = value;
    if (!dirty && document.activeElement !== temperatureTargetInput) temperatureTargetInput.value = value.toFixed(1);
    renderTemperatureTarget();
}

async function saveTemperatureTarget() {
    const state = temperatureTargetState;
    if (state.saving || state.saved === null) return;
    const value = Number(temperatureTargetInput.value);
    if (!temperatureTargetInput.value.trim() || !Number.isFinite(value) || value < 40 || value > 71) {
        alert("Anna lämpötilatavoite väliltä 40–71 °C.");
        return;
    }
    state.saving = true;
    state.error = false;
    renderTemperatureTarget();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
        const response = await fetch("/api/heater/control", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({temperature_target: value}), signal: controller.signal
        });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const result = await response.json();
        if (result.temperature_target !== value) throw new Error("Palvelin ei vahvistanut lämpötilatavoitetta");
        state.saved = value;
    } catch (error) {
        state.error = true;
        console.error("Temperature target save failed:", error);
    } finally {
        clearTimeout(timer);
        state.saving = false;
        renderTemperatureTarget();
    }
}

if (temperatureTargetInput && temperatureTargetButton) {
    temperatureTargetInput.addEventListener("input", () => {
        temperatureTargetState.edited = true;
        temperatureTargetState.error = false;
        renderTemperatureTarget();
    });
    temperatureTargetButton.addEventListener("click", saveTemperatureTarget);
    renderTemperatureTarget();
}

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
