'''Bot helper process.'''

import queue
import time

from rlbot.botmanager.agent_metadata import AgentMetadata
from rlbot.botmanager.bot_helper_process import BotHelperProcess
from rlbot.utils import rate_limiter
from rlbot.utils.logging_utils import get_logger
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
from rlbot.utils.structures.ball_prediction_struct import BallPrediction
from rlbot.utils.structures.game_interface import GameInterface

import data

class Hivemind(BotHelperProcess):

    def __init__(self, agent_metadata_queue, quit_event, options):
        super().__init__(agent_metadata_queue, quit_event, options)
        self.logger = get_logger('Hivemind')
        self.game_interface = GameInterface(self.logger)
        self.running_indices = set()

    def try_receive_agent_metadata(self):
        while True:  # will exit on queue.Empty
            try:
                single_agent_metadata: AgentMetadata = self.metadata_queue.get(timeout=0.1)
                self.running_indices.add(single_agent_metadata.index)
            except queue.Empty:
                return
            except Exception as ex:
                self.logger.error(ex)


    def start(self):
        """Runs once, sets up the hivemind and its bots."""
        # Prints stuff into the console.
        self.logger.info("Hivemind A C T I V A T E D")
        self.logger.info("Breaking the meta")
        self.logger.info("Welcoming r0bbi3")
        
        # Loads game interface.
        self.game_interface.load_interface()

        # Wait a moment for all agents to have a chance to start up and send metadata.
        time.sleep(1)
        self.try_receive_agent_metadata()
        
        # Runs the game loop where the hivemind will spend the rest of its time.
        self.game_loop()

            
    def game_loop(self):
        """The main game loop. This is where your hivemind code goes."""

        # Setting up rate limiter.
        rate_limit = rate_limiter.RateLimiter(120)

        # Setting up data.
        field_info = FieldInfoPacket()
        self.game_interface.update_field_info_packet(field_info)
        data.setup(self, self.running_indices, field_info)

        # The loop.
        while True:
            # Updating the game packet from the game.
            packet = GameTickPacket()
            self.game_interface.update_live_data_packet(packet)
    
            # Processing packet.
            data.process(self, packet)

            # Ball prediction.
            ball_predict = BallPrediction()
            self.game_interface.update_ball_prediction(ball_predict)
            self.ball.predict = ball_predict

            locations = [step.physics.location for step in ball_predict.slices]
            self.game_interface.renderer.begin_rendering()
            self.game_interface.renderer.draw_polyline_3d(locations, self.game_interface.renderer.pink())
            self.game_interface.renderer.end_rendering()

            # For each bot under the hivemind's control, do something.
            for index in self.running_indices:

                ctrl = PlayerInput() # Basically the same as SimpleControllerState().

                # TEST
                ctrl.throttle = 1.0
                ctrl.steer = (-1.0)**index

                # Send the controls to the bots.
                self.game_interface.update_player_input(ctrl, index)

            # Rate limit sleep.
            rate_limit.acquire()