model harness_user_model "Tiny user model to verify Dymola can compile a user .mo from the headless harness"
  parameter Real tau = 0.5 "first-order time constant [s]";
  parameter Real y0 = 0.0 "initial state";
  parameter Real y_inf = 1.0 "asymptotic value";
  Real y(start = y0, fixed = true);
equation
  tau * der(y) = y_inf - y;
end harness_user_model;
