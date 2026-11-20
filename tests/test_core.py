import copy
import itertools
import unittest

from pipe_hold import TraceError, audit


def pipe(process="root", ident="p", read=3, write=4, flag=False):
    return dict(op="pipe", process=process, pipe=ident, read_fd=read, write_fd=write, cloexec=flag)


def event(op, process="root", **values):
    return dict(op=op, process=process, **values)


def run(events, holders=8):
    return audit({"root": "root", "events": events}, holders=holders)


class LifecycleTests(unittest.TestCase):
    def test_parent_reference_survives_writer_exit(self):
        result = run([pipe(), event("fork", child="writer"), event("fork", child="reader"),
                      event("close", "reader", fd=4), event("exit", "writer"),
                      event("expect_eof", "reader", fd=3)])
        check = result["checks"][0]
        self.assertEqual(check["writer_descriptors"], 1)
        self.assertEqual(check["holders"][0]["process"], "root")
        self.assertEqual(check["self_held_writers"], 0)

    def test_self_reference_and_aliases_count_individually(self):
        result = run([pipe(), event("dup2", src=4, dst=5), event("expect_eof", fd=3)])
        check = result["checks"][0]
        self.assertEqual((check["writer_descriptors"], check["writer_processes"], check["self_held_writers"]), (2, 1, 2))
        self.assertEqual(check["holders"][1]["source"], {"process":"root", "fd":4, "created_event":1})

    def test_close_and_later_repair_keep_historical_failure(self):
        result = run([pipe(), event("expect_eof", fd=3), event("close", fd=4), event("expect_eof", fd=3)])
        self.assertEqual([c["eof_after_drain"] for c in result["checks"]], [False, True])
        self.assertEqual(result["failed_checks"], 1)
        self.assertTrue(result["gate_failed"])
        self.assertEqual(result["checks"][0]["holders"][0]["fd"], 4)

    def test_dup2_clears_cloexec_but_self_dup_preserves_it(self):
        result = run([pipe(flag=True), event("dup2", src=3, dst=0), event("dup2", src=4, dst=1),
                      event("dup2", src=4, dst=4), event("exec"), event("expect_eof", fd=0)])
        h = result["checks"][0]["holders"]
        self.assertEqual(len(h), 1)
        self.assertEqual((h[0]["fd"], h[0]["created_event"], h[0]["cloexec"]), (1, 3, False))
        self.assertEqual(result["live_descriptors"], 2)

    def test_flag_is_per_descriptor_and_per_process(self):
        result = run([pipe(), event("fork", child="child"),
                      event("set_cloexec", fd=4, value=True), event("exec"),
                      event("expect_eof", fd=3), event("exit", "child"), event("expect_eof", fd=3)])
        self.assertEqual(result["checks"][0]["holders"][0]["process"], "child")
        self.assertFalse(result["checks"][0]["holders"][0]["cloexec"])
        self.assertTrue(result["checks"][1]["eof_after_drain"])

    def test_fork_copies_cloexec_and_keeps_child_after_parent_exit(self):
        result = run([pipe(flag=True), event("set_cloexec", fd=3, value=False),
                      event("fork", child="child"), event("exit"),
                      event("expect_eof", "child", fd=3), event("exec", "child"),
                      event("expect_eof", "child", fd=3)])
        first = result["checks"][0]
        self.assertEqual(first["holders"][0]["source"], {"process":"root", "fd":4, "created_event":1})
        self.assertTrue(first["holders"][0]["cloexec"])
        self.assertTrue(result["checks"][1]["eof_after_drain"])

    def test_replacing_writer_with_other_pipe_read_releases_original(self):
        result = run([pipe(), pipe(ident="other", read=6, write=7),
                      event("dup2", src=6, dst=4), event("expect_eof", fd=3),
                      event("expect_eof", fd=4)])
        self.assertTrue(result["checks"][0]["eof_after_drain"])
        self.assertFalse(result["checks"][1]["eof_after_drain"])
        self.assertEqual(result["checks"][1]["pipe"], "other")

    def test_descriptor_reuse_has_new_creation_provenance(self):
        result = run([pipe(), event("dup2", src=4, dst=5), event("close", fd=4),
                      event("dup2", src=5, dst=4), event("close", fd=5), event("expect_eof", fd=3)])
        ref = result["checks"][0]["holders"][0]
        self.assertEqual(ref["created_event"], 4)
        self.assertEqual(ref["source"], {"process":"root", "fd":5, "created_event":2})

    def test_holder_cap_does_not_change_counts_or_gate(self):
        events = [pipe(), event("dup2", src=4, dst=5), event("fork", child="alpha"), event("expect_eof", fd=3)]
        full = run(events)
        for cap in [0, 1, 2]:
            limited = run(events, holders=cap)
            check = limited["checks"][0]
            self.assertEqual(check["writer_descriptors"], 4)
            self.assertEqual(check["omitted_holders"], 4-cap)
            self.assertEqual(check["holders"], full["checks"][0]["holders"][:cap])
            self.assertEqual(limited["gate_failed"], full["gate_failed"])

    def test_input_is_not_mutated(self):
        doc = {"root":"root", "events":[pipe(), event("expect_eof", fd=3)]}
        old = copy.deepcopy(doc)
        audit(doc)
        self.assertEqual(old, doc)

    def test_exhaustive_alias_lifetime_definition(self):
        # Six independently owned writer descriptors after duplication and forks.
        # Oracle: keep survives exec; close and close-on-exec do not. No nested
        # descriptor-table replay or production helpers are used for expectation.
        slots = [(p, fd) for p in ["root", "alpha", "beta"] for fd in [4, 5]]
        comparisons = 0
        for choices in itertools.product(range(3), repeat=6):
            events = [pipe(), event("dup2", src=4, dst=5),
                      event("fork", child="alpha"), event("fork", child="beta")]
            for (p, fd), choice in zip(slots, choices):
                if choice == 1:
                    events.append(event("close", p, fd=fd))
                elif choice == 2:
                    events.append(event("set_cloexec", p, fd=fd, value=True))
            events.extend(event("exec", p) for p in ["root", "alpha", "beta"])
            events.append(event("expect_eof", fd=3))
            surviving = sorted(slot for slot, choice in zip(slots, choices) if choice == 0)
            for cap in [0, 1, 8]:
                result = run(events, holders=cap)
                check = result["checks"][0]
                self.assertEqual(check["writer_descriptors"], len(surviving))
                self.assertEqual(check["writer_processes"], len({p for p, _ in surviving}))
                self.assertEqual(check["self_held_writers"], sum(p == "root" for p, _ in surviving))
                self.assertEqual([(h["process"], h["fd"]) for h in check["holders"]], surviving[:cap])
                self.assertEqual(result["gate_failed"], bool(surviving))
                comparisons += 1
        self.assertEqual(comparisons, 2187)


class InvalidTraceTests(unittest.TestCase):
    def bad(self, events):
        with self.assertRaises(TraceError):
            run(events)

    def test_schema_and_values(self):
        for doc in [None, [], {}, {"root":"root", "events":[]}, {"root":"bad\n", "events":[event("expect_eof", fd=3)]}]:
            with self.assertRaises(TraceError):
                audit(doc)
        for change in [{"fd":True}, {"fd":-1}, {"fd":64}, {"fd":3.0}, {"extra":1}, {"op":"write"}]:
            self.bad([pipe(), {**event("expect_eof", fd=3), **change}])
        self.bad([{**pipe(), "cloexec":1}, event("expect_eof", fd=3)])
        for cap in [-1, 33, True, "1"]:
            with self.assertRaises(TraceError):
                run([pipe(), event("expect_eof", fd=3)], holders=cap)

    def test_invalid_descriptor_and_process_lifetimes(self):
        for action in [event("close", fd=1), event("dup2", src=9, dst=4),
                       event("expect_eof", fd=4), event("close", "unknown", fd=3),
                       pipe(read=3, write=3), pipe(ident="other")]:
            self.bad([pipe(), action, event("expect_eof", fd=3)])
        self.bad([pipe(), event("exit"), event("expect_eof", fd=3)])
        self.bad([pipe(), event("fork", child="child"), event("exit", "child"),
                  event("fork", child="child"), event("expect_eof", fd=3)])
        self.bad([pipe(), event("close", fd=3), event("close", fd=4), pipe(), event("expect_eof", fd=3)])

    def test_resource_limits(self):
        self.bad([pipe()] + [event("expect_eof", fd=3)]*65)
        self.bad([pipe()] + [event("exec")]*511 + [event("expect_eof", fd=3)])
        self.bad([pipe()] + [event("fork", child=f"p{i}") for i in range(32)] + [event("expect_eof", fd=3)])
        self.bad([pipe(ident=f"p{i}",read=i*2,write=i*2+1) for i in range(17)] + [event("expect_eof", fd=0)])
        events = [pipe()] + [event("dup2", src=4, dst=fd) for fd in range(64) if fd not in [3, 4]]
        self.bad(events + [event("fork",child=f"p{i}") for i in range(4)] + [event("expect_eof",fd=3)])

    def test_no_checks_is_invalid(self):
        self.bad([pipe()])
