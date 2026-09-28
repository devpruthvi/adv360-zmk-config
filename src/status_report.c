/*
 * Pushes a 32-byte status report to the host over raw HID whenever the
 * active layer, battery level or output changes, and on request (host sends
 * "Z?"). Read by cli/adv360-status. Layout, little-endian:
 *
 *   0     'Z' magic
 *   1     protocol version (1)
 *   2     highest active layer index
 *   3-6   active layer bitmask
 *   7     left battery % (0xFF unknown)
 *   8     right battery % (0xFF unknown)
 *   9     transport: 0 none, 1 USB, 2 BLE
 *   10    BLE profile index
 *   11    BLE profile connected
 *   12-31 active layer name, NUL padded
 */

#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/byteorder.h>

#include <raw_hid/events.h>

#include <zmk/battery.h>
#include <zmk/ble.h>
#include <zmk/endpoints.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define REPORT_MAGIC 'Z'
#define REPORT_VERSION 1
#define REPORT_NAME_OFFSET 12
#define BATTERY_UNKNOWN 0xFF

static uint8_t right_battery = BATTERY_UNKNOWN;

static void send_status(struct k_work *work) {
    static uint8_t report[CONFIG_RAW_HID_REPORT_SIZE];
    memset(report, 0, sizeof(report));

    zmk_keymap_layer_index_t index = zmk_keymap_highest_layer_active();
    zmk_keymap_layers_state_t state = zmk_keymap_layer_state();
    struct zmk_endpoint_instance endpoint = zmk_endpoint_get_selected();

    report[0] = REPORT_MAGIC;
    report[1] = REPORT_VERSION;
    report[2] = index;
    sys_put_le32(state, &report[3]);
    report[7] = zmk_battery_state_of_charge();
    report[8] = right_battery;
    report[9] = endpoint.transport;
#if IS_ENABLED(CONFIG_ZMK_BLE)
    int profile = zmk_ble_active_profile_index();
    report[10] = profile;
    report[11] = zmk_ble_profile_is_connected(profile);
#endif

    const char *name = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(index));
    if (name != NULL) {
        strncpy((char *)&report[REPORT_NAME_OFFSET], name,
                CONFIG_RAW_HID_REPORT_SIZE - REPORT_NAME_OFFSET - 1);
    }

    raise_raw_hid_sent_event(
        (struct raw_hid_sent_event){.data = report, .length = sizeof(report)});
}

// Sent from a work item so a slow transport never stalls keymap processing
static K_WORK_DEFINE(status_work, send_status);

static int status_listener(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *peripheral =
        as_zmk_peripheral_battery_state_changed(eh);
    if (peripheral != NULL) {
        right_battery = peripheral->state_of_charge;
    }

    k_work_submit(&status_work);
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(adv360_status, status_listener);
ZMK_SUBSCRIPTION(adv360_status, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(adv360_status, zmk_battery_state_changed);
ZMK_SUBSCRIPTION(adv360_status, zmk_peripheral_battery_state_changed);
ZMK_SUBSCRIPTION(adv360_status, zmk_endpoint_changed);
#if IS_ENABLED(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(adv360_status, zmk_ble_active_profile_changed);
#endif

static int query_listener(const zmk_event_t *eh) {
    const struct raw_hid_received_event *event = as_raw_hid_received_event(eh);
    if (event != NULL && event->length >= 2 && event->data[0] == REPORT_MAGIC &&
        event->data[1] == '?') {
        k_work_submit(&status_work);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(adv360_status_query, query_listener);
ZMK_SUBSCRIPTION(adv360_status_query, raw_hid_received_event);
