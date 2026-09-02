# API Design & Security Rules
Rule API-001: Endpoints should expose only the fields a client actually needs; avoid returning entire internal objects by default.
Rule API-002: State-changing operations should use appropriate HTTP methods and should not be triggerable via a simple GET request.
Rule API-003: Error responses should avoid leaking internal implementation details such as stack traces or raw exception messages.
Rule API-004: New or experimental endpoints should be reviewed for consistency with existing authentication and authorization patterns before release.
Rule API-005: Publicly readable endpoints should only return information that is safe to expose without authentication.
