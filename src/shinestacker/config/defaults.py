# pylint: disable=C0114
import os

DEFAULTS = {
    'expert_options': False,
    'view_strategy': 'overlaid',
    'paint_refresh_time': 50,  # ms
    'display_refresh_time': 50,  # ms
    'cursor_update_time': 16,  # ms
    'min_mouse_step_brush_fraction': 0.25,
    'stack_algo': 'Pyramid',
    'sequential_task': {
        'max_threads': 8,
        'chunk_submit': True
    },
    'image_sequence_manager': {
        'reverse_order': False,
        'plots_path': 'plots'
    },
    'reference_frame_task': {
        'step_process': True
    },
    'combined_actions_params': {
        'max_threads': min(os.cpu_count() or 4, 8),
    },
    'align_frames_params': {
        'memory_limit': 8,  # GB
        'max_threads': min(os.cpu_count() or 4, 8),
        'detector': 'ORB',
        'descriptor': 'ORB',
        'match_method': 'NORM_HAMMING',
        'subsample': 0
    },
    'focus_stack_params': {
        'memory_limit': 8,  # GB
        'max_threads': min(os.cpu_count() or 4, 8)
    },
    'focus_stack_bunch_params': {
        'memory_limit': 8,  # GB
        'max_threads': min(os.cpu_count() or 4, 8)
    },
    'noise_detection': {
        'noise_map_filename': 'hot_pixels.png',
        'max_frames': 10
    },
    'multilayer': {
        'file_reverse_order': True
    }
}
