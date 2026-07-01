param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$ContainerGroup,

    [Parameter(Mandatory = $true)]
    [string]$Image,

    [Parameter(Mandatory = $true)]
    [string]$ExcelFlowUrl
)

az container create `
  --resource-group $ResourceGroup `
  --name $ContainerGroup `
  --image $Image `
  --restart-policy Never `
  --cpu 1 --memory 1.5 `
  --environment-variables `
    EXCEL_FLOW_URL=$ExcelFlowUrl `
    LOOKBACK_DAYS=1 `
    LOOKAHEAD_DAYS=7
