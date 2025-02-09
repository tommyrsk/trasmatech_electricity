# TrasMaTech - Electricity Meter
Custom Integration for integrating Electricity Meter that use HAN / API.

For the moment there is only support for the Norwegian OSS-device used by Å Strøm.<br>
(More updates will arrive)

Per time (temporary): the "token" and "meter id" needs to be extracted out after authenticated through the https://api.services.oss.no/swagger/index.html<br>
(and yes, you need to have a registered email address from OSS that you are getting the authsecret on, that you need to use)

## Temporary Procedure (step-by-step):
1. "Authentication step 1: Start authentication procedure"
2. "Authentication step 2: Complete authentication procedure"
   - _authid is result from step 1, and authSecret is coming to your email_
3. Now you need to "Authorize" with the token you got in step 2.
   _authorize is own button up to right above the list of commands_
4: "Authentication step 3: Creates a new Public API token for this account"
   - _Suggesting to set "expires" to one year ahead._
   - _Suggesting to set "friendlyName" to "HomeAssistant"_
   - Take care of this encodedToken, you need it for the HomeAssistant as **token**. If you loose it, you have to create a new one
5. Now you need to logout "Authorize". And ReAuthorize with the token you got in step 4.
   - _authorize is own button up to right above the list of commands_
6. "Get meters for an account"<br>
   - Read out the **meterNumber** from the result, you need it for the HomeAssistant.
   
