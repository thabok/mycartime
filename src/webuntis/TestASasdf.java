package webuntis;

import java.util.Map;
import java.util.Map.Entry;

public class TestASasdf {

	public static void main(String[] args) throws Exception {
//		String sessionId = WebUntisAdapter.login("", "");
//		System.out.println(sessionId);
		
//		WebUntisAdapter.sessionId = "";
		String teacherInitials = "";
		Map<Integer, TimetableItem> timetable = WebUntisAdapter.getTimetable(teacherInitials);
		System.out.println("Timetable for " + teacherInitials + ":\n");
		for (Entry<Integer, TimetableItem> entry : timetable.entrySet()) {
			System.out.println(entry.getKey() + ": [" + entry.getValue().startTime + " - " + entry.getValue().endTime + "]");
		}
	}

}
