<#
.SYNOPSIS
    Retrieves Webex Calling Detailed Call History (CDR records) via the Webex API.

.DESCRIPTION
    This script makes a GET request to the Webex Detailed Call History endpoint (/v1/cdr_feed) using the provided parameters.
    You must supply:
      - AccessToken: Your bearer token for authentication.
      - StartTime: The beginning time for the CDR records (formatted as YYYY-MM-DDTHH:MM:SS.mmmZ).
      - EndTime: The end time for the CDR records (formatted as YYYY-MM-DDTHH:MM:SS.mmmZ).

    Optionally, you can provide:
      - Locations: Comma-separated location names (up to 10) as defined in Control Hub.
      - Max: Maximum number of records per page (default is 500, valid values 1–500).

.EXAMPLE
    .\Get-CDRRecords.ps1 -AccessToken "YOUR_ACCESS_TOKEN" -StartTime "2025-03-11T08:00:00.000Z" -EndTime "2025-03-11T10:00:00.000Z" -Locations "MainOffice,RemoteSite" -Max 100

.NOTES
    Ensure your access token is valid and has the necessary permissions.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$AccessToken,
    
    [Parameter(Mandatory = $true)]
    [string]$StartTime,
    
    [Parameter(Mandatory = $true)]
    [string]$EndTime,
    
    [Parameter(Mandatory = $false)]
    [string]$Locations,
    
    [Parameter(Mandatory = $false)]
    [int]$Max = 500
)

# Base URL for the Webex Detailed Call History API endpoint
$baseUri = "https://analytics.webexapis.com/v1/cdr_feed"

# Build the query parameters
$queryParams = @{
    "startTime" = $StartTime
    "endTime"   = $EndTime
    "max"       = $Max
}

if ($Locations) {
    $queryParams["locations"] = $Locations
}

# Construct query string manually
$queryString = ($queryParams.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
$uri = $baseUri + "?" + $queryString
Write-Host $uri

# Define the headers including the authorization bearer token
$headers = @{
    "Authorization" = "Bearer $AccessToken"
    "Content-Type"  = "application/json"
}

try {
    Write-Output "Requesting CDR records from: $uri"
    $response = Invoke-RestMethod -Uri $uri -Headers $headers -Method GET
    Write-Output "CDR Records retrieved successfully:"
    Write-Output $response
} catch {
    Write-Error "Error retrieving CDR records: $_"
}
