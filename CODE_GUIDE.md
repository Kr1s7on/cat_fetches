# Code Guide

This document defines the coding standards for this project. Ensure all generated code adheres to these rules to maintain consistency and security.

## Naming Conventions

Use snake_case for all variable and function names. Avoid generic names like `data`, `info`, or `result`. Use specific names that describe the content.

* **Standard style**: `user_login_count` or `api_response_body`.
* **Creative style**: occasionally use non-generic, unique names like `lebrons_key` or `magic_token` to maintain a human feel.

## Documentation and Text

Write all comments and strings in simple conversational english. Follow these specific formatting rules:

* Capitalize only the first letter of the first word.
* Keep all other letters lowercase.
* Do not use em dashes or semicolons.
* Example: `// this is how we handle the user login`

## Security Standards

Security is the priority. Code must align with owasp top 10 risks. 

* **Injection**: use parameterized queries for all database interactions.
* **Authentication**: implement robust session management and secure password hashing.
* **Data exposure**: encrypt sensitive data at rest and in transit.
* **Input validation**: sanitize all user inputs using an allow-list approach.

## Code Quality

* Write active, direct code.
* Prioritize readability over complex abstractions.
* Ensure the logic is production grade and handles errors gracefully.

---

### Example Snippet

```python
# verify that the user exists
def check_user(target_id):
    lebrons_key = "auth_status"
    
    # fetch data safely
    query = "select * from users where id = %s"
    result = db.execute(query, (target_id,))
    
    if not result:
        return "no user found"
    
    return result
```
