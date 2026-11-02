
import os
import logging

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    inference,
)
from livekit.plugins import simli


# ==========================================
# 1. Load Environment Variables
# ==========================================

load_dotenv(".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mateo-ai-avatar")


# ==========================================
# 2. Mateo AI Assistant
# ==========================================

class MateoAssistant(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            YOUR IDENTITY:
            Your name is Mateo.

            You are Mateo, a friendly, intelligent,
            confident and professional AI assistant
            in a real-time video meeting.

            You are visually represented by the
            photorealistic Mateo avatar in this meeting.

            IMPORTANT IDENTITY RULES:
            - Your name is Mateo.
            - If someone asks your name, respond:
              "My name is Mateo."
            - If someone calls you Mateo, respond
              naturally and acknowledge the name.
            - Do not deny that your name is Mateo.
            - If asked whether you are the Mateo
              shown on screen, explain that you are
              the AI assistant represented by that
              avatar.
            - You are an AI assistant, not a human.
            - Do not claim to be a real person.

            PERSONALITY:
            - Friendly and approachable.
            - Confident and professional.
            - Conversational and engaging.
            - Helpful and intelligent.
            - Natural and expressive.

            CONVERSATION BEHAVIOR:
            - Give clear and concise responses.
            - Speak naturally, as in a video meeting.
            - Avoid long speeches unless requested.
            - Avoid Markdown formatting.
            - Listen carefully to the user.
            - Respond to questions directly.
            - Allow natural interruptions.
            - Ask clarifying questions when needed.
            - Never invent information when unsure.

            LANGUAGE:
            - Speak English by default.
            - Use another language when requested,
              if supported by the voice pipeline.

            INTRODUCTION:
            When introducing yourself, say
            something similar to:

            "Hey! I'm Mateo, your AI assistant.
            It's great to meet you.
            How can I help you today?"

            REMEMBER:
            Your identity throughout this meeting
            is Mateo, the AI assistant.
            """
        )


# ==========================================
# 3. Create LiveKit Agent Server
# ==========================================

server = AgentServer()


# ==========================================
# 4. Register Named Agent
# ==========================================

@server.rtc_session(agent_name="avatar-agent")
async def avatar_agent(ctx: agents.JobContext):

    logger.info("Mateo AI agent job received")
    logger.info("Room: %s", ctx.room.name)

    try:

        # ==================================
        # 5. Real-Time Voice Pipeline
        # ==================================

        session = AgentSession(

            # Speech recognition
            stt=inference.STT(
                model="deepgram/flux-general",
                language="en",
            ),

            # AI language model
            llm=inference.LLM(
                model="google/gemma-4-31b-it",
            ),

            # Voice synthesis
            tts=inference.TTS(
                model="fishaudio/s2.1-pro",
                voice="fa4c9eb3dccc4806b382b40d61c6b10a",
            ),

        )

        logger.info("Mateo voice pipeline initialized")

        # ==================================
        # 6. Simli Avatar Integration
        # ==================================

        enable_simli = (
            os.getenv("ENABLE_SIMLI", "false")
            .strip()
            .lower() == "true"
        )

        if enable_simli:

            simli_key = os.getenv("SIMLI_API_KEY")
            face_id = os.getenv("SIMLI_FACE_ID")

            if not simli_key or not face_id:
                raise ValueError(
                    "SIMLI_API_KEY and SIMLI_FACE_ID "
                    "must be configured in .env"
                )

            logger.info("Initializing Mateo Simli avatar")

            avatar = simli.AvatarSession(
                simli_config=simli.SimliConfig(
                    api_key=simli_key,
                    face_id=face_id,
                )
            )

            await avatar.start(
                session,
                room=ctx.room,
            )

            logger.info("Mateo Simli avatar initialized")

        else:
            logger.info("Simli disabled: voice-only mode")

        # ==================================
        # 7. Start LiveKit Session
        # ==================================

        await session.start(
            room=ctx.room,
            agent=MateoAssistant(),
        )

        logger.info("Mateo AI voice session started")

        # ==================================
        # 8. Connect to LiveKit Room
        # ==================================

        await ctx.connect()

        logger.info("Mateo connected to LiveKit room")

        # ==================================
        # 9. Greeting
        # ==================================

        await session.generate_reply(
            instructions=(
                "Greet the participant warmly. "
                "Introduce yourself by saying "
                "your name is Mateo and explain "
                "that you are their AI assistant. "
                "Ask how you can help them today. "
                "Keep the greeting short and natural."
            )
        )

        logger.info("Mateo greeting generated")

    except Exception:
        logger.exception(
            "Error while running Mateo AI avatar"
        )
        raise


# ==========================================
# 10. Run LiveKit Worker
# ==========================================

if __name__ == "__main__":
    agents.cli.run_app(server)
