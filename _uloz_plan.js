global.set("fve_plan", msg.payload);
global.set("fve_current_mode", msg.payload.currentMode);

msg.ha_update = {
    state: msg.payload.currentMode,
    attributes: {
        current_mode: msg.payload.currentMode,
        current_reason: msg.payload.currentReason,
        current_hour: msg.payload.currentHour,
        plan: msg.payload.plan,
        soc: msg.payload.status.soc,
        forecast_dnes: msg.payload.status.forecastDnes,
        forecast_zitra: msg.payload.status.forecastZitra,
        last_update: msg.payload.generatedAt,
        debug: msg.payload.debug || {},
        blokace_text: msg.payload.status.blokaceText || "NE"
    }
};

return msg;