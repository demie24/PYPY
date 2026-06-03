interface SafetyState {
  threatScore: number;
  trustScore: number;
  attackActive: boolean;
}

export const validateMobileCommand = (
  action: string,
  target: string,
  state: SafetyState
): { valid: boolean; reason?: string } => {
  // Rule C: Trust Validation Gate
  if (state.trustScore < 90) {
    return {
      valid: false,
      reason: `SAFETY INTERCEPT: Telemetry trust score is degraded (${state.trustScore.toFixed(1)}% < 90.0%). Automatic controls locked.`
    };
  }

  // Rule D: Cyberattack Remote Override Gate
  if (state.attackActive && state.threatScore > 70) {
    return {
      valid: false,
      reason: "SAFETY INTERCEPT: Active cyber-physical intrusion detected with threat index > 70%. Remote override commands suspended."
    };
  }

  // Rule E: Critical Infrastructure Protection
  const generatorBuses = ["Bus_1", "Bus_2", "Bus_3", "Bus_4"];
  if (action === "isolate_bus" && generatorBuses.includes(target)) {
    return {
      valid: false,
      reason: `SAFETY INTERCEPT: Target ${target} is classified as critical generation infrastructure. Remote islanding is prohibited.`
    };
  }

  return { valid: true };
};
