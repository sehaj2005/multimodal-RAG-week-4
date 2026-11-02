import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

import {
  LiveKitRoom,
  ParticipantTile,
  ControlBar,
  RoomAudioRenderer,
  useTracks,
  TrackRefContext,
} from '@livekit/components-react';

import { Track } from 'livekit-client';
import '@livekit/components-styles';
import './style.css';

type Credentials = {
  meeting_id: string;
  livekit_url: string;
  access_token: string;
};

const API = 'http://127.0.0.1:8000';

// ==========================================
// Two-person meeting interface
// ==========================================

function TwoPersonMeeting() {
  const tracks = useTracks(
    [{ source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false }
  );

  // Show only local human + Simli avatar
  const visibleTracks = tracks.filter((trackRef) => {
    const participant = trackRef.participant;

    return (
      participant.isLocal ||
      participant.identity.startsWith('simli-')
    );
  });

  return (
    <div className="two-person-meeting">
      <div className="meeting-videos custom-grid">
        {visibleTracks.map((trackRef, index) => {
          const participant = trackRef.participant;

          let displayName = participant.name || participant.identity;

          if (participant.isLocal) {
            displayName = 'Human Participant';
          } else if (participant.identity.startsWith('simli-')) {
            displayName = 'Mateo';
          }

          return (
            <div
              className="custom-tile"
              key={`${participant.identity}-${index}`}
            >
              <TrackRefContext.Provider value={trackRef}>
                <ParticipantTile />
              </TrackRefContext.Provider>

              <div className="custom-name">
                {displayName}
              </div>
            </div>
          );
        })}
      </div>

      <RoomAudioRenderer />

      <div className="meeting-controls">
        <ControlBar
          variation="minimal"
          controls={{
            microphone: true,
            camera: true,
            screenShare: true,
            chat: false,
            leave: true,
          }}
        />
      </div>
    </div>
  );
}

// ==========================================
// Main app
// ==========================================

function App() {
  const [credentials, setCredentials] =
    useState<Credentials | null>(null);

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function startMeeting() {
    setError('');
    setLoading(true);

    try {
      // 1. Create meeting
      const meetingResponse = await fetch(
        `${API}/api/v1/meetings`,
        { method: 'POST' }
      );

      if (!meetingResponse.ok) {
        throw new Error(
          `Meeting creation failed: ${meetingResponse.status}`
        );
      }

      const meeting = await meetingResponse.json();

      // 2. Join as human participant
      const joinResponse = await fetch(
        `${API}/api/v1/meetings/${meeting.meeting_id}/join`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            display_name: 'Human Participant',
            role: 'human',
          }),
        }
      );

      if (!joinResponse.ok) {
        throw new Error(
          `Meeting join failed: ${joinResponse.status}`
        );
      }

      const joinData: Credentials =
        await joinResponse.json();

      setCredentials(joinData);

      // 3. Start AI agent
      try {
        const agentResponse = await fetch(
          `${API}/api/v1/meetings/${meeting.meeting_id}/agent/start`,
          { method: 'POST' }
        );

        if (!agentResponse.ok) {
          setError(
            `Agent dispatch failed (${agentResponse.status}).`
          );
        }
      } catch (agentError) {
        console.error('Agent dispatch error:', agentError);
        setError('Unable to start AI agent.');
      }

    } catch (err) {
      console.error('Meeting error:', err);

      setError(
        err instanceof Error ? err.message : String(err)
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Realtime AI Avatar</h1>
        <span>Human + Mateo AI</span>
      </header>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {!credentials ? (
        <section className="landing">
          <h2>Meet your AI assistant</h2>
          <p>
            Have a real-time conversation with Mateo,
            your photorealistic AI assistant.
          </p>

          <button
            onClick={startMeeting}
            disabled={loading}
          >
            {loading ? 'Connecting...' : 'Start meeting'}
          </button>
        </section>
      ) : (
        <section className="meeting">
          <LiveKitRoom
            token={credentials.access_token}
            serverUrl={credentials.livekit_url}
            connect={true}
            audio={true}
            video={true}
            onDisconnected={() => setCredentials(null)}
            data-lk-theme="default"
          >
            <TwoPersonMeeting />
          </LiveKitRoom>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);