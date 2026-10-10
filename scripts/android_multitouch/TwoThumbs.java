import java.lang.reflect.Array;
import java.lang.reflect.Method;

public class TwoThumbs {
    private static final int ACTION_DOWN = 0;
    private static final int ACTION_UP = 1;
    private static final int ACTION_MOVE = 2;
    private static final int ACTION_POINTER_DOWN = 5;
    private static final int ACTION_POINTER_UP = 6;
    private static final int SOURCE_TOUCHSCREEN = 0x00001002;
    private static final int TOOL_TYPE_FINGER = 1;
    private static final int INJECT_ASYNC = 0;
    private static final long FRAME_MS = 16L;

    private final Object inputManager;
    private final Method injectMethod;
    private final Class<?> motionEventClass;
    private final Class<?> propertiesClass;
    private final Class<?> coordsClass;
    private final Method uptimeMethod;

    public static void main(String[] args) throws Exception {
        if (args.length != 5) {
            throw new IllegalArgumentException("usage: TwoThumbs leftX leftY rightX rightY holdMs");
        }
        float leftX = Float.parseFloat(args[0]);
        float leftY = Float.parseFloat(args[1]);
        float rightX = Float.parseFloat(args[2]);
        float rightY = Float.parseFloat(args[3]);
        long holdMs = Long.parseLong(args[4]);
        TwoThumbs thumbs = new TwoThumbs();
        thumbs.playTwoFingerPress(leftX, leftY, rightX, rightY, holdMs);
    }

    public TwoThumbs() throws Exception {
        Class<?> serviceManager = Class.forName("android.os.ServiceManager");
        Object binder = serviceManager.getMethod("getService", String.class).invoke(null, "input");
        Class<?> inputManagerInterface = findInputManagerInterface();
        Class<?> stub = Class.forName(inputManagerInterface.getName() + "$Stub");
        Class<?> binderClass = Class.forName("android.os.IBinder");
        this.inputManager = stub.getMethod("asInterface", binderClass).invoke(null, binder);
        this.injectMethod = inputManagerInterface.getMethod(
                "injectInputEvent", Class.forName("android.view.InputEvent"), int.class);
        this.motionEventClass = Class.forName("android.view.MotionEvent");
        this.propertiesClass = Class.forName("android.view.MotionEvent$PointerProperties");
        this.coordsClass = Class.forName("android.view.MotionEvent$PointerCoords");
        this.uptimeMethod = Class.forName("android.os.SystemClock").getMethod("uptimeMillis");
    }

    private static Class<?> findInputManagerInterface() throws ClassNotFoundException {
        try {
            return Class.forName("android.hardware.input.IInputManager");
        } catch (ClassNotFoundException notMovedYet) {
            return Class.forName("android.view.IInputManager");
        }
    }

    public void playTwoFingerPress(float leftX, float leftY, float rightX, float rightY, long holdMs)
            throws Exception {
        long downTime = (Long) uptimeMethod.invoke(null);
        inject(downTime, ACTION_DOWN, new float[] {leftX}, new float[] {leftY}, downTime);
        inject(downTime, ACTION_POINTER_DOWN | (1 << 8),
                new float[] {leftX, rightX}, new float[] {leftY, rightY}, downTime);
        long holdEnd = System.currentTimeMillis() + holdMs;
        while (System.currentTimeMillis() < holdEnd) {
            Thread.sleep(FRAME_MS);
            inject(downTime, ACTION_MOVE, new float[] {leftX, rightX}, new float[] {leftY, rightY}, downTime);
        }
        inject(downTime, ACTION_POINTER_UP | (1 << 8),
                new float[] {leftX, rightX}, new float[] {leftY, rightY}, downTime);
        inject(downTime, ACTION_UP, new float[] {leftX}, new float[] {leftY}, downTime);
    }

    private void inject(long downTime, int action, float[] xs, float[] ys, long eventDownTime)
            throws Exception {
        int count = xs.length;
        Object properties = Array.newInstance(propertiesClass, count);
        Object coords = Array.newInstance(coordsClass, count);
        for (int index = 0; index < count; index++) {
            Object property = propertiesClass.getConstructor().newInstance();
            propertiesClass.getField("id").setInt(property, index);
            propertiesClass.getField("toolType").setInt(property, TOOL_TYPE_FINGER);
            Array.set(properties, index, property);
            Object coord = coordsClass.getConstructor().newInstance();
            coordsClass.getField("x").setFloat(coord, xs[index]);
            coordsClass.getField("y").setFloat(coord, ys[index]);
            coordsClass.getField("pressure").setFloat(coord, 1.0f);
            coordsClass.getField("size").setFloat(coord, 1.0f);
            Array.set(coords, index, coord);
        }
        long now = (Long) uptimeMethod.invoke(null);
        Method obtain = motionEventClass.getMethod("obtain",
                long.class, long.class, int.class, int.class,
                Array.newInstance(propertiesClass, 0).getClass(),
                Array.newInstance(coordsClass, 0).getClass(),
                int.class, int.class, float.class, float.class,
                int.class, int.class, int.class, int.class);
        Object event = obtain.invoke(null, eventDownTime, now, action, count,
                properties, coords, 0, 0, 1.0f, 1.0f, 0, 0, SOURCE_TOUCHSCREEN, 0);
        Boolean accepted = (Boolean) injectMethod.invoke(inputManager, event, INJECT_ASYNC);
        if (!accepted) {
            throw new IllegalStateException("injectInputEvent refused action " + action);
        }
    }
}
