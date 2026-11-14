# Ejecuta las corridas del ejercicio de experimentacion en modo no-GUI.
# Antes de cada corrida reinicia la API (los datos viven en memoria) y al final genera el reporte HTML.
#
# Uso (desde pruebas/experimentacion):
#   .\ejecutar_experimentos.ps1                       # todas las corridas
#   .\ejecutar_experimentos.ps1 -Corridas p01_20u,p01_500u
#
# Requisitos: JMeter 5.6.3 con los plugins jpgc (Standard Set y PerfMon), Python 3 y,
# para P05 y P10, el ServerAgent corriendo en el puerto 4444.

param(
    [string[]]$Corridas = @(),
    [string]$JMeterBin = "C:\apache-jmeter-5.6.3\bin\jmeter.bat"
)

$ErrorActionPreference = "Stop"
$aqui = $PSScriptRoot
$repo = Resolve-Path (Join-Path $aqui "..\..")
$api = Join-Path $repo "api\ticketmania_simple.py"

# Cada corrida cambia una sola variable respecto a su par.
# granularidad: segundos por punto en las graficas del reporte HTML.
$todas = @(
    @{ id = "p01_20u";        plan = "P01_carga_usuarios.jmx";              props = @{ usuarios = 20 };                                        gran = 1000 }
    @{ id = "p01_500u";       plan = "P01_carga_usuarios.jmx";              props = @{ usuarios = 500 };                                       gran = 1000 }
    @{ id = "p02_subida1";    plan = "P02_rampup.jmx";                      props = @{ subida = 1 };                                           gran = 1000 }
    @{ id = "p02_subida60";   plan = "P02_rampup.jmx";                      props = @{ subida = 60 };                                          gran = 1000 }
    @{ id = "p03_con_timer";  plan = "P03_temporizadores.jmx";              props = @{ hilos_con = 50; hilos_sin = 0 };                        gran = 1000 }
    @{ id = "p03_sin_timer";  plan = "P03_temporizadores.jmx";              props = @{ hilos_con = 0;  hilos_sin = 50 };                       gran = 1000 }
    @{ id = "p04_escalones";  plan = "P04_estres_escalones.jmx";            props = @{};                                                       gran = 1000 }
    @{ id = "p05_1min";       plan = "P05_duracion.jmx";                    props = @{ duracion = 60 };                                        gran = 1000 }
    @{ id = "p05_10min";      plan = "P05_duracion.jmx";                    props = @{ duracion = 600 };                                       gran = 10000 }
    @{ id = "p06_lectura_1";  plan = "P06_costo_endpoints.jmx";             props = @{ hilos_lectura = 200; hilos_escritura = 0 };             gran = 1000 }
    @{ id = "p06_escritura_1";plan = "P06_costo_endpoints.jmx";             props = @{ hilos_lectura = 0;   hilos_escritura = 200 };           gran = 1000 }
    @{ id = "p06_lectura_2";  plan = "P06_costo_endpoints.jmx";             props = @{ hilos_lectura = 200; hilos_escritura = 0 };             gran = 1000 }
    @{ id = "p06_escritura_2";plan = "P06_costo_endpoints.jmx";             props = @{ hilos_lectura = 0;   hilos_escritura = 200 };           gran = 1000 }
    @{ id = "p07_rep1";       plan = "P07_concurrencia_reservas.jmx";       props = @{};                                                       gran = 1000 }
    @{ id = "p07_rep2";       plan = "P07_concurrencia_reservas.jmx";       props = @{};                                                       gran = 1000 }
    @{ id = "p07_rep3";       plan = "P07_concurrencia_reservas.jmx";       props = @{};                                                       gran = 1000 }
    @{ id = "p08_sincronizado";plan = "P08_sincronizado_vs_distribuido.jmx"; props = @{ hilos_sinc = 300; hilos_dist = 0 };                    gran = 1000 }
    @{ id = "p08_distribuido";plan = "P08_sincronizado_vs_distribuido.jmx"; props = @{ hilos_sinc = 0;   hilos_dist = 300 };                   gran = 1000 }
    @{ id = "p09_carga";      plan = "P09_total_cobrado.jmx";               props = @{};                                                       gran = 1000 }
    @{ id = "p09_control";    plan = "P09_total_cobrado.jmx";               props = @{ archivo_datos = "datos_total_control.csv"; usuarios = 12; subida = 1; bucles = 1 }; gran = 1000 }
    @{ id = "p10_50u";        plan = "P10_recursos.jmx";                    props = @{ usuarios = 50 };                                        gran = 1000 }
    @{ id = "p10_500u";       plan = "P10_recursos.jmx";                    props = @{ usuarios = 500 };                                       gran = 1000 }
)

if ($Corridas.Count -gt 0) { $todas = $todas | Where-Object { $Corridas -contains $_.id } }

function Iniciar-Api {
    $p = Start-Process -FilePath "python" -ArgumentList "`"$api`"" -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:8080/api/salud"
            if ($r.Content -match "OK") { return $p }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    throw "La API no respondio en /api/salud"
}

Set-Location $aqui
New-Item -ItemType Directory -Force (Join-Path $aqui "resultados") | Out-Null

foreach ($c in $todas) {
    $salida = Join-Path $aqui "resultados\$($c.id)"
    if (Test-Path $salida) { Remove-Item -Recurse -Force $salida }
    New-Item -ItemType Directory -Force $salida | Out-Null

    $proc = Iniciar-Api
    $jargs = @("-n", "-t", $c.plan,
              "-l", "$salida\resultados.jtl",
              "-j", "$salida\jmeter.log",
              "-e", "-o", "$salida\reporte",
              "-Jjmeter.reportgenerator.overall_granularity=$($c.gran)",
              "-Jsample_variables=num_reserva",
              "-Jpid_api=$($proc.Id)",
              "-Jarchivo_perfmon=$salida\perfmon.csv")
    foreach ($k in $c.props.Keys) { $jargs += "-J$k=$($c.props[$k])" }

    $inicio = Get-Date
    Write-Host "== $($c.id): $($c.plan) $($c.props | ConvertTo-Json -Compress) (API pid $($proc.Id))"
    & $JMeterBin @jargs | Out-File -Encoding utf8 "$salida\consola.txt"
    $fin = Get-Date

    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    "{0},{1},{2},{3}" -f $c.id, $c.plan, $inicio.ToString("s"), $fin.ToString("s") |
        Add-Content -Encoding utf8 (Join-Path $aqui "resultados\bitacora.csv")
}
