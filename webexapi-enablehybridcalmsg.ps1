#
# Script to enable Hybrid Calendar and Hybrid Messaging for all Webex users.
#

# API Bearer Token for Authentication
$webex_access_token = Read-Host -Prompt "Go to https://developer.webex.com/docs/api/getting-started and get your personal access token, then paste it here:"

# Get Licenses
$webex_license_uri = "https://webexapis.com/v1/licenses"
$webex_license_parameters = @{
  Uri = $webex_license_uri
  Headers = @{
    'authorization' = "Bearer $webex_access_token"
  }
}
$webex_license_json = Invoke-RestMethod @webex_license_parameters
#echo $webex_license_json.items
foreach ($license in $webex_license_json.items) {
	if ($license.name -eq "Hybrid - Exchange Calendar") {
		$hybridcal = $license.id
	}
	if ($license.name -eq "Hybrid - Message") {
		$hybridmsg = $license.id
	}
}

# Get User Details
$webex_user_uri = "https://webexapis.com/v1/people?max=1000"

$user_parameters = @{
  Uri = $webex_user_uri
  Headers = @{
    'authorization' = "Bearer $webex_access_token"
  }
}
$user_json = Invoke-RestMethod @user_parameters

foreach ($user in $user_json.items) {
	if ($user.loginenabled) {
		echo "----------------"
		echo $user.displayName
		echo $user.emails
		echo $user.id
		$update = $false
		if ($user.licenses.contains($hybridcal)) {
			echo "hybridcal enabled"
		} else {
			echo "adding hybridcal"
			$user.licenses += $hybridcal
			$update = $true
		}
		if ($user.licenses.contains($hybridmsg)) {
			echo "hybridmsg enabled"
		} else {
			echo "adding hybridmsg"
			$user.licenses += $hybridmsg
			$update = $true
		}
		if ($update) {
			echo "posting updated user licenses"
			$put_json = $user | ConvertTo-JSON
			$put_parameters = @{
				Uri = "https://webexapis.com/v1/people/" + $user.id
				Method = "Put"
				Body = $put_json
				ContentType = "application/json"
				Headers = @{
					'authorization' = "Bearer $webex_access_token"
				}
			}
			Invoke-RestMethod @put_parameters

		}
	}
}
