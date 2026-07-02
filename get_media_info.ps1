# get_media_info.ps1
# Queries the Windows Media Session API (GSMTC) for Spotify playback info.
# Outputs a single JSON line with title, artist, album, duration, status.

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

    function Await($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }

    [void][Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime]

    $smType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]
    $sessionManager = Await ($smType::RequestAsync()) ($smType)

    $sessions = $sessionManager.GetSessions()

    foreach ($session in $sessions) {
        $sourceId = $session.SourceAppUserModelId

        if ($sourceId -match "(?i)spotify") {
            $mpType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties]
            $mediaProps = Await ($session.TryGetMediaPropertiesAsync()) ($mpType)

            $playbackInfo = $session.GetPlaybackInfo()
            $timeline = $session.GetTimelineProperties()

            $obj = [ordered]@{
                source         = [string]$sourceId
                title          = [string]$mediaProps.Title
                artist         = [string]$mediaProps.Artist
                albumTitle     = [string]$mediaProps.AlbumTitle
                albumArtist    = [string]$mediaProps.AlbumArtist
                trackNumber    = [int]$mediaProps.TrackNumber
                playbackStatus = [string]$playbackInfo.PlaybackStatus
                endTime        = [math]::Round($timeline.EndTime.TotalSeconds, 1)
                position       = [math]::Round($timeline.Position.TotalSeconds, 1)
            }

            try   { $obj.playbackType = $mediaProps.PlaybackType.Value.ToString() }
            catch { $obj.playbackType = "Unknown" }

            $obj | ConvertTo-Json -Compress
            exit 0
        }
    }

    # No Spotify session found
    Write-Output '{"error":"no_spotify_session"}'

} catch {
    $msg = $_.Exception.Message -replace '["\\/]', ' '
    Write-Output "{`"error`":`"$msg`"}"
}
