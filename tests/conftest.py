from hypothesis import HealthCheck, Verbosity, settings

# Define Hypothesis profiles
settings.register_profile(
    "default",
    max_examples=100,
    deadline=1000,
    suppress_health_check=[HealthCheck.differing_executors],
)
settings.register_profile(
    "ci", max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.differing_executors]
)
settings.register_profile(
    "debug",
    max_examples=10,
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.differing_executors],
)

settings.load_profile("default")
