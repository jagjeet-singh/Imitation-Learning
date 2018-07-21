import sys
import argparse
import numpy as np
import keras
import random
import gym
import pdb
from termcolor import cprint
from logger import Logger


class Imitation():
    def __init__(self, model_config_path, expert_weights_path):
        # Load the expert model.
        with open(model_config_path, 'r') as f:
            self.expert = keras.models.model_from_json(f.read())
        self.expert.load_weights(expert_weights_path)
        
        # Initialize the cloned model (to be trained).
        with open(model_config_path, 'r') as f:
            self.model = keras.models.model_from_json(f.read())
        # TODO: Define any training operations and optimizers here, initialize
        #       your variables, or alternatively compile your model here.
        # Compile model
        # pdb.set_trace()
        self.model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])


    def run_expert(self, env, render=False):
        # Generates an episode by running the expert policy on the given env.
        return Imitation.generate_episode(self.expert, env, render)

    def run_model(self, env, render=False):
        # Generates an episode by running the cloned policy on the given env.
        return Imitation.generate_episode(self.model, env, render)

    @staticmethod
    def generate_episode(model, env, render=False):
        # Generates an episode by running the given model on the given env.
        # Returns:
        # - a list of states, indexed by time step
        # - a list of actions, indexed by time step
        # - a list of rewards, indexed by time step
        # TODO: Implement this method.

        done = False
        nS = env.observation_space.shape[0]
        nA = env.action_space.n
        states = np.zeros((0,nS))
        actions = np.zeros((0, nA))
        rewards = np.zeros((0))
        state = env.reset()
        while not done:
            if render:
                env.render()
            state = np.reshape(state, (1,nS))
            action_softmax = model.predict(state)
            action = np.argmax(action_softmax)
            next_state, reward, done, _ = env.step(action)
            states = np.append(states, state, axis=0)
            action = np.eye(nA)[action].reshape(1,nA)            
            actions = np.append(actions, action, axis=0)
            rewards = np.append(rewards,reward)
            state = next_state.copy()
        return states, actions, rewards
    
    def train(self, env, num_episodes=100, num_epochs=50, render_interval=5, eval_episodes=50, render=False, logger=None):
        # Trains the model on training data generated by the expert policy.
        # Args:
        # - env: The environment to run the expert policy on. 
        # - num_episodes: # episodes to be generated by the expert.
        # - num_epochs: # epochs to train on the data generated by the expert.
        # - render: Whether to render the environment.
        # Returns the final loss and accuracy.
        # TODO: Implement this method. It may be helpful to call the class
        #       method run_expert() to generate training data.
        args = parse_arguments()

        for epoch in range(num_epochs):
            for epi in range(num_episodes):
                states, actions, rewards = self.run_expert(env)
                # hist = self.model.fit(states, actions, epochs=num_epochs, verbose=0)
                hist = self.model.fit(states, actions, epochs=1, verbose=0)
                if epi%render_interval==0:
                    self.run_model(env,render)
            loss = hist.history['loss'][-1]
            acc = hist.history['acc'][-1]

            logger.scalar_summary(tag='Train/loss', value=loss, step=epoch)
            logger.scalar_summary(tag='Train/acc', value=acc, step=epoch)

        # Calculate rewards for 50 episodes
            
            if epoch%args.eval_freq == 0:
                model_rewards = []

                # Running Model
                
                print('Evaluating for Model ...')
                for epi in range(eval_episodes):
                    _,_,rewards = self.run_model(env)
                    model_rewards.append(np.sum(rewards))
                print("Model Rewards - N {} - epoch {} : Mean({}), Std({})"\
                	.format(num_episodes, epoch, np.mean(model_rewards), np.std(model_rewards)))
                logger.scalar_summary(tag='Val/mean', value=np.mean(model_rewards), step=epoch)
                logger.scalar_summary(tag='Val/std', value=np.std(model_rewards), step=epoch)
        
        # Running Expert
        print('Evaluating for Expert ...')
        expert_rewards = []
        for epi in range(eval_episodes):
                _,_,rewards = self.run_expert(env)
                expert_rewards.append(np.sum(rewards))
        cprint("Expert Rewards - N {}: Mean({}), Std({})"\
                .format(num_episodes,np.mean(expert_rewards), np.std(expert_rewards)),
                color='green')
        return loss, acc


def parse_arguments():
    # Command-line flags are defined here.
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-config-path', dest='model_config_path',
                        type=str, default='LunarLander-v2-config.json',
                        help="Path to the model config file.")
    parser.add_argument('--expert-weights-path', dest='expert_weights_path',
                        type=str, default='LunarLander-v2-weights.h5',
                        help="Path to the expert weights file.")
    parser.add_argument('--eval-freq', default=5, help='Frequency of evaluation')
    # https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    parser_group = parser.add_mutually_exclusive_group(required=False)
    parser_group.add_argument('--render', dest='render',
                              action='store_true',
                              help="Whether to render the environment.")
    parser_group.add_argument('--no-render', dest='render',
                              action='store_false',
                              help="Whether to render the environment.")
    parser.set_defaults(render=False)

    return parser.parse_args()


def main(args):
    # Parse command-line arguments.
    args = parse_arguments()
    model_config_path = args.model_config_path
    expert_weights_path = args.expert_weights_path
    render = args.render
    
    # Create the environment.
    env = gym.make('LunarLander-v2')
    episode_list = [1, 10, 50, 100]
    epoch_list = [10000, 1000, 50, 50]
    # TODO: Train cloned models using imitation learning, and record their
    #       performance.
    for i in range(len(episode_list)):
        logger = Logger('hw3_logs', name='LunarLander-v2_imitation_N'+str(episode_list[i]))
        imi = Imitation(model_config_path, expert_weights_path)
        loss, acc = imi.train(env, num_episodes=episode_list[i], render=render, logger=logger, num_epochs=epoch_list[i])
        cprint("Loss after training for {} expert episodes is {}".format(episode_list[i], loss), color='red')
        cprint("Accuracy after training for {} expert episodes is {}".format(episode_list[i], acc), color='red')

if __name__ == '__main__':
  main(sys.argv)
